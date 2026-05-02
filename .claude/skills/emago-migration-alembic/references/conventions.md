# Conventions Alembic Emago

Règles consolidées tirées des 6 migrations existantes (`alembic/versions/0001_*` → `0006_*`) et de `docs/07_base_de_donnees.md`.

## 1. Structure de fichier

- Nom : `0001_initial_schema.py`, `0002_seed_scar_tags.py`, etc. (4 chiffres + underscore + nom snake_case).
- `revision = '0007'` (string, padding 4 chars).
- `down_revision = '0006'` (string, ou `None` pour la première).
- Toujours `upgrade()` ET `downgrade()` (jamais juste un sens).
- Docstring en haut : description courte + Revision ID + Create Date.

## 2. Types de colonnes

| Cas Emago | Type SQLAlchemy / Postgres | Notes |
|---|---|---|
| ID primaire | `postgresql.UUID(as_uuid=True), server_default=text("gen_random_uuid()")` | Toujours UUID sauf scar_tags |
| ID auto-incrémenté | `sa.Integer, primary_key=True, autoincrement=True` | scar_tags uniquement |
| Texte court | `sa.String(N)` avec longueur explicite | username 32, tag 8, name 64 |
| Texte long | `sa.Text` | description, narrative |
| Stat / niveau | `sa.SmallInteger` | grade 0-5, system 1-499 |
| Coût ressource | `sa.Integer` | cost_metal, cost_crystal |
| Stock ressource | `sa.Numeric(16, 2)` | metal, crystal, deuterium (précision décimale) |
| Score | `sa.BigInteger` | score joueur, alliance |
| XP | `sa.Integer` | combat_xp |
| Capacité | `sa.Integer` | metal_capacity |
| Bool | `sa.Boolean, server_default='false'` | is_completed, is_recalled |
| JSONB extensible | `postgresql.JSONB, server_default='{}'` ou `'[]'` | base_stats, payload, rounds_log |
| Timestamp | `postgresql.TIMESTAMP(timezone=True)` | always timezone aware |
| Enum | `sa.String + CHECK constraint` ou `postgresql.ENUM` selon cas | préférer String + CHECK pour souplesse |

## 3. Server defaults

Toujours utiliser `server_default=sa.text(...)` pour générer côté BDD :

```python
server_default=sa.text("gen_random_uuid()")              # UUID
server_default=sa.text("now()")                          # timestamp
server_default=sa.text("now() + INTERVAL '8 hours'")     # forge completed_at
server_default='0'                                       # numeric
server_default="''"                                      # string
server_default='false'                                   # bool
server_default="'{}'"                                    # JSONB dict
server_default="'[]'"                                    # JSONB list
```

## 4. Enums Postgres

Les **types ENUM Postgres** sont utilisés mais les **colonnes** Emago utilisent `sa.String` côté SQLAlchemy avec CHECK constraint, pour faciliter les évolutions futures.

### Création
```python
op.execute("CREATE TYPE ship_class AS ENUM ('ATTACK', 'DEFENSE', 'SUPPORT', 'EXPLORATION')")
```

### Usage en colonne
```python
sa.Column('class', sa.String, nullable=False)
sa.CheckConstraint("class IN ('ATTACK', 'DEFENSE', 'SUPPORT', 'EXPLORATION')", name='ck_ship_class')
```

OU directement avec ENUM PG :
```python
sa.Column('class', postgresql.ENUM(name='ship_class', create_type=False), nullable=False)
```

### Drop
```python
op.execute("DROP TYPE IF EXISTS ship_class")
```

## 5. Foreign Keys

### Cascade par défaut
```python
sa.ForeignKey('players.id', ondelete='CASCADE')   # supprime enfants si parent supprimé
sa.ForeignKey('planets.id', ondelete='SET NULL')  # garde l'enfant avec NULL
sa.ForeignKey('alliances.id', ondelete='RESTRICT')# refuse suppression si enfants existent
```

### FK circulaires (alliance ↔ player)

Quand 2 tables se référencent mutuellement :

```python
# Étape 1 : créer alliances avec leader_id en use_alter (FK différée)
op.create_table('alliances',
    sa.Column('id', ...),
    sa.Column('leader_id', postgresql.UUID(as_uuid=True),
              sa.ForeignKey('players.id', use_alter=True, name='fk_alliance_leader'),
              nullable=False),
    ...
)

# Étape 2 : créer players avec alliance_id en use_alter
op.create_table('players',
    sa.Column('id', ...),
    sa.Column('alliance_id', postgresql.UUID(as_uuid=True),
              sa.ForeignKey('alliances.id', use_alter=True, ondelete='SET NULL'),
              nullable=True),
    ...
)
```

## 6. Indexes

### Index simple
```python
op.create_index('idx_xxx_field', 'xxx', ['field'])
```

### Index multi-colonnes
```python
op.create_index('idx_xxx_owner_status', 'xxx', ['owner_id', 'status'])
```

### Index DESC (pour ranking)
```python
op.create_index('idx_players_score', 'players', [sa.text('score DESC')])
```

### Index partiel — **CRITIQUE pour scheduler**
```python
op.execute("""
    CREATE INDEX idx_xxx_pending
    ON xxx (completes_at)
    WHERE is_completed = FALSE
""")
```

Indexes partiels existants Emago :
- `idx_build_queue_planet_pending` — build_queue scheduler 10s
- `idx_forge_queue_completed_at` — forge scheduler 60s
- `idx_fleets_arrives_at` — fleet scheduler 5s
- `idx_ship_missions_ship_expires` — missions actives
- `idx_expedition_completes_at` — expéditions
- `idx_alliance_wars_active` — wars actives
- `idx_ships_is_drift` — ships dérivés (rare, utile pour stats)

### Drop index partiel (en raw SQL)
```python
op.execute("DROP INDEX IF EXISTS idx_xxx_pending")
```

## 7. Constraints

### CHECK
```python
sa.CheckConstraint('grade BETWEEN 0 AND 5', name='ck_ship_grade')
sa.CheckConstraint('combat_xp >= 0', name='ck_ship_xp_positive')
sa.CheckConstraint("status IN ('ACTIVE', 'PEACE')", name='ck_war_status')
sa.CheckConstraint('attacker_id != defender_id', name='ck_war_distinct_alliances')
```

### UNIQUE
```python
sa.UniqueConstraint('username', name='uq_players_username')           # mono-colonne
sa.UniqueConstraint('galaxy', 'system', 'position', name='uq_planet_coordinates')
sa.UniqueConstraint('ship_id', 'slot_index', name='uq_ship_module_slot')
sa.UniqueConstraint('player_id', name='uq_alliance_members_player')   # 1 alliance par joueur
```

## 8. Triggers PG

### Auto-update updated_at
```python
op.execute("""
    CREATE OR REPLACE FUNCTION set_updated_at_fn()
    RETURNS TRIGGER AS $$
    BEGIN NEW.updated_at = now(); RETURN NEW; END;
    $$ LANGUAGE plpgsql;
""")
op.execute("""
    CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON ships
    FOR EACH ROW EXECUTE FUNCTION set_updated_at_fn();
""")
```

### Immuabilité avec bypass session var
```python
op.execute("""
    CREATE OR REPLACE FUNCTION prevent_xxx_update_fn()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.xxx IS DISTINCT FROM OLD.xxx
           AND COALESCE(current_setting('emago.bypass_xxx_trigger', true), '') != 'true'
        THEN
            RAISE EXCEPTION 'xxx is immutable after creation'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
""")
op.execute("""
    CREATE TRIGGER prevent_xxx_update
    BEFORE UPDATE ON xxx_table
    FOR EACH ROW EXECUTE FUNCTION prevent_xxx_update_fn();
""")
```

### Drop trigger + fonction
```python
op.execute("DROP TRIGGER IF EXISTS prevent_xxx_update ON xxx_table")
op.execute("DROP FUNCTION IF EXISTS prevent_xxx_update_fn()")
```

## 9. Bulk insert (seeds)

```python
my_table = sa.table('scar_tags',
    sa.column('tag_code', sa.String),
    sa.column('narrative', sa.Text),
)
op.bulk_insert(my_table, [
    {'tag_code': 'nebula_kha_survivor', 'narrative': 'Rescapé de la Nébuleuse Kha'},
    {'tag_code': 'siege_anneau_iv',     'narrative': 'Survivant du Siège de l\'Anneau IV'},
])
```

Pour seeds idempotents (re-run safe) :
```python
op.execute("""
    INSERT INTO scar_tags (tag_code, narrative)
    VALUES ('born_in_drift', 'Né dans la Dérive')
    ON CONFLICT (tag_code) DO NOTHING
""")
```

## 10. Migration de données

Quand on ajoute une colonne et qu'il faut remplir les rows existantes :

```python
def upgrade():
    op.add_column('ships', sa.Column('is_drift', sa.Boolean, nullable=False, server_default='false'))
    # Pas besoin d'UPDATE explicite, server_default remplit tout

    # Cas plus complexe : remplissage conditionnel
    op.execute("""
        UPDATE ships
        SET is_drift = true
        WHERE jsonb_typeof(base_stats) = 'object'
          AND base_stats->>'forged_with_drift' = 'true'
    """)
```

## 11. Bypass de trigger pour migration

Si une migration doit modifier une colonne immuable (rare mais arrive en cas de refonte) :

```python
def upgrade():
    op.execute("SET LOCAL emago.bypass_stats_trigger = 'true'")
    op.execute("UPDATE ships SET base_stats = ... WHERE ...")
    op.execute("SET LOCAL emago.bypass_stats_trigger = ''")
```

## 12. Idempotence

Les migrations doivent être idempotentes autant que possible :

- `CREATE EXTENSION IF NOT EXISTS pgcrypto`
- `DROP TRIGGER IF EXISTS xxx ON yyy`
- `INSERT ... ON CONFLICT DO NOTHING`
- `op.add_column` automatiquement idempotent si table existe

Mais Alembic ne re-applique pas une migration déjà flagged → idempotence interne pas nécessaire pour le upgrade lui-même, juste pour les commandes raw.

## 13. Anti-patterns à éviter

- ❌ Modifier `base_stats` sans bypass session var → trigger raise.
- ❌ Drop colonne sans considérer la perte de données.
- ❌ Migration trop grosse (> 500 lignes) → splitter en plusieurs.
- ❌ Modifier des données utilisateur sans backup préalable en prod.
- ❌ `op.execute` au lieu d'API Alembic quand cette dernière marche (préférer `op.add_column`, `op.create_index`, etc.).
- ❌ Forgetting `down_revision` ou doublonner.
- ❌ Renommer une colonne directement → préférer ajouter nouvelle colonne + migration de données + drop ancienne en plusieurs migrations.
