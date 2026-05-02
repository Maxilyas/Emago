---
name: emago-migration-alembic
description: Génère une migration Alembic pour Emago en respectant toutes les conventions du projet — UUID PK avec gen_random_uuid(), enums PostgreSQL miroirs des Python, indexes partiels pour scheduler (WHERE is_completed=FALSE), triggers BEFORE UPDATE pour immuabilité (cf. prevent_base_stats_update), FK avec cascade adapté, FK circulaires via use_alter=True, JSONB pour données extensibles, NUMERIC(16,2) pour ressources, BigInt pour scores, partial indexes critiques, bypass session var emago.bypass_stats_trigger pour migrations contrôlées. Sortie un fichier alembic/versions/000X_<name>.py avec upgrade() + downgrade() complets. Use when l'utilisateur dit "migration Alembic", "ajoute table", "alter ships", "nouvelle table BDD", "migration espionnage", "schéma marché galactique".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 7-dev-bdd
---

# emago-migration-alembic

Génère des migrations Alembic conformes aux conventions Emago. Encapsule les patterns du schéma initial et des 5 migrations existantes (0001 → 0006).

---

## Quand utiliser ce skill

- Ajouter une nouvelle table (espionage_reports, market_offers, player_module_inventory…).
- ALTER TABLE existante (nouvelles colonnes, contraintes, indexes).
- Créer un nouveau enum PostgreSQL.
- Seeder des données de référence (ex. tags narratifs, événements).
- Ajouter / modifier un trigger d'intégrité.

## Quand NE PAS utiliser ce skill

- Pour le modèle SQLAlchemy correspondant → à compléter en parallèle dans `app/models/models.py` ou un nouveau fichier `app/models/<feature>_models.py`.
- Pour seed massif (>10k rows) → utiliser script ad hoc, pas une migration.
- Pour modifier `base_stats` après création → **interdit** (trigger PG le bloque).

---

## Instructions

### Étape 1 — Cadrer la migration

Demande à l'utilisateur :

1. **Nature** : nouvelle table / ALTER existante / nouveau enum / seed / trigger ?
2. **Nom court** (kebab-case ou underscore_case) qui décrit la migration. Sera dans le nom de fichier.
3. **Contenu détaillé** :
   - Pour table : nom, colonnes (type Postgres + contraintes), indexes, FK.
   - Pour ALTER : table cible, opérations.
   - Pour enum : nom, valeurs.
   - Pour seed : table cible, données.
4. **Migration de remplissage** des données existantes (le cas échéant) : comment gérer les rows existantes après ALTER ?

### Étape 2 — Vérifier la dernière migration

```bash
ls alembic/versions/ | sort
```

Identifier la dernière (`down_revision`). La nouvelle aura `revision = "000X"` avec `X = max + 1` (padding 4 chiffres).

### Étape 3 — Vérifier les conventions

#### IDs primaires
```python
sa.Column('id', postgresql.UUID(as_uuid=True),
          primary_key=True,
          server_default=sa.text("gen_random_uuid()"))
```

#### Enums Postgres
```python
# Création
op.execute("CREATE TYPE my_enum AS ENUM ('VAL1', 'VAL2', 'VAL3')")
# Usage en colonne
sa.Column('status', postgresql.ENUM(name='my_enum', create_type=False), nullable=False)
# Downgrade
op.execute("DROP TYPE my_enum")
```

> **Note Emago** : on utilise `String` côté SQLAlchemy en colonne (pas `Enum`) — facilite l'évolution. Le type PG existe quand même côté BDD.

#### Timestamps
```python
sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
          nullable=False,
          server_default=sa.text("now()"))
```

#### Ressources (NUMERIC pour précision)
```python
sa.Column('metal', sa.Numeric(16, 2), nullable=False, server_default='0')
sa.Column('cost_metal', sa.Integer, nullable=False, default=0)  # coût = entier
```

#### Score / XP (BigInt)
```python
sa.Column('score', sa.BigInteger, nullable=False, server_default='0')
sa.Column('combat_xp', sa.Integer, sa.CheckConstraint('combat_xp >= 0'), default=0)
```

#### JSONB extensible
```python
sa.Column('payload', postgresql.JSONB, nullable=False, server_default='{}')
sa.Column('items', postgresql.JSONB, nullable=False, server_default='[]')
```

#### Foreign Keys avec ON DELETE
```python
sa.Column('player_id', postgresql.UUID(as_uuid=True),
          sa.ForeignKey('players.id', ondelete='CASCADE'),
          nullable=False)
# CASCADE : supprime les enfants (ship_modules, scars, missions)
# SET NULL : garde l'orphelin avec NULL (planets.owner_id si player supprimé)
# RESTRICT : refuse la suppression si enfants existent
```

#### Indexes partiels (CRITIQUES pour scheduler)

```python
# Index partiel : WHERE actif uniquement → minimise scans scheduler
op.execute("""
    CREATE INDEX idx_xxx_pending
    ON my_table (completes_at)
    WHERE is_completed = FALSE
""")
```

#### CHECK constraints
```python
sa.CheckConstraint('grade BETWEEN 0 AND 5', name='ck_ship_grade')
sa.CheckConstraint("status IN ('ACTIVE', 'PEACE')", name='ck_war_status')
sa.CheckConstraint('attacker_id != defender_id', name='ck_war_different_alliances')
```

#### UNIQUE multi-colonnes
```python
sa.UniqueConstraint('galaxy', 'system', 'position', name='uq_planet_coordinates')
sa.UniqueConstraint('ship_id', 'slot_index', name='uq_ship_module_slot')
```

#### FK circulaires (alliance ↔ player)
```python
# Étape 1 : créer table A sans FK vers B
# Étape 2 : créer table B avec FK vers A use_alter
# Étape 3 : ajouter FK A → B après les deux

sa.Column('leader_id', postgresql.UUID(as_uuid=True),
          sa.ForeignKey('players.id', use_alter=True, name='fk_alliance_leader'),
          nullable=False)
```

#### Triggers BEFORE UPDATE
```python
# Cas général : timestamp update_at
op.execute("""
    CREATE OR REPLACE FUNCTION set_updated_at_fn()
    RETURNS TRIGGER AS $$
    BEGIN NEW.updated_at = now(); RETURN NEW; END;
    $$ LANGUAGE plpgsql;
""")
op.execute("""
    CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON my_table
    FOR EACH ROW EXECUTE FUNCTION set_updated_at_fn();
""")

# Cas immuabilité (cf. prevent_base_stats_update) : utiliser bypass session var
op.execute("""
    CREATE OR REPLACE FUNCTION prevent_my_field_update_fn()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.my_field IS DISTINCT FROM OLD.my_field
            AND COALESCE(current_setting('emago.bypass_my_trigger', true), '') != 'true'
        THEN
            RAISE EXCEPTION 'my_field is immutable after creation'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
""")
```

#### Extensions Postgres
```python
# Toujours dans la première migration. Pas besoin de re-créer dans les suivantes.
op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
```

### Étape 4 — Générer le code

Utilise `references/migration_template.py` comme base. Toujours fournir `upgrade()` ET `downgrade()` (idempotent dans la mesure du possible).

### Étape 5 — Mettre à jour les modèles SQLAlchemy

Après la migration, mettre à jour ou créer le modèle correspondant dans `app/models/` (si pas déjà fait par Agent 5/7) :

```python
# app/models/<feature>_models.py
from app.models.models import Base

class MyTable(Base):
    __tablename__ = "my_table"
    # ... colonnes alignées avec la migration ...
```

### Étape 6 — Tester

```bash
# Apply
docker compose exec api alembic upgrade head

# Check schema
docker compose exec db psql -U emago -d emago -c "\dt"
docker compose exec db psql -U emago -d emago -c "\d my_table"

# Test downgrade
docker compose exec api alembic downgrade -1

# Re-apply
docker compose exec api alembic upgrade head
```

### Étape 7 — Mise à jour `docs/07_base_de_donnees.md`

- Section 3 : ajouter la nouvelle table avec colonnes, contraintes, indexes.
- Section 5 : compléter l'historique des migrations.

---

## Examples

### Exemple 1 — Nouvelle table (espionage_reports)

**User** : "Migration Alembic pour ajouter la table espionage_reports"

**Actions** :
1. Vérifie : dernière migration = 0006.
2. Génère `alembic/versions/0007_espionage_reports.py` :
   - `id UUID PK gen_random_uuid()`.
   - `prober_id UUID FK players(id) ON DELETE CASCADE`.
   - `target_planet_id UUID FK planets(id) ON DELETE SET NULL`.
   - `target_player_id UUID FK players(id) ON DELETE SET NULL`.
   - `prober_tech_level SMALLINT NOT NULL`.
   - `result JSONB NOT NULL DEFAULT '{}'` (resources observed, fleet observed, buildings observed).
   - `detected BOOLEAN NOT NULL DEFAULT FALSE`.
   - `launched_at TIMESTAMPTZ DEFAULT now()`.
   - `arrives_at TIMESTAMPTZ NOT NULL`.
   - `completed_at TIMESTAMPTZ`.
3. Indexes :
   - `idx_espionage_prober` (prober_id).
   - `idx_espionage_target_planet` (target_planet_id).
   - Index partiel `idx_espionage_pending` (arrives_at) WHERE `completed_at IS NULL`.
4. CHECK : `prober_tech_level >= 1`.
5. Downgrade : drop indexes puis table.
6. Met à jour `docs/07_base_de_donnees.md` section 3.

### Exemple 2 — ALTER ajout colonne (flag défensif)

**User** : "Ajouter une colonne `is_garrisoned` BOOLEAN sur ships pour identifier les ships en mode défense passive"

**Actions** :
1. Génère `alembic/versions/0008_ships_is_garrisoned.py` :
   ```python
   def upgrade():
       op.add_column('ships',
           sa.Column('is_garrisoned', sa.Boolean,
                     nullable=False,
                     server_default='false'))
       # Index partiel uniquement les ships garrisoned
       op.execute("""
           CREATE INDEX idx_ships_garrisoned
           ON ships (owner_id, planet_id)
           WHERE is_garrisoned = true
       """)
   ```
2. Pas de remplissage requis (default `false`).
3. Downgrade : drop index + drop column.

### Exemple 3 — Nouveau enum + colonne enum

**User** : "Ajouter un enum `mission_type` pour les missions de vaisseau, valeurs : COMBAT, EXPLORATION, TRADE, ESPIONAGE"

**Actions** :
1. `op.execute("CREATE TYPE mission_type AS ENUM ('COMBAT', 'EXPLORATION', 'TRADE', 'ESPIONAGE')")`.
2. ALTER ship_missions : remplacer `mission_type VARCHAR(64)` par `mission_type mission_type` ? **Attention** : si rows existantes utilisent des valeurs différentes, il faut un mapping.
3. Migration de données : `UPDATE ship_missions SET mission_type = 'COMBAT' WHERE mission_type NOT IN (...)`.
4. Downgrade : revert vers VARCHAR.

### Exemple 4 — Seed scar tags supplémentaires

**User** : "Ajouter 50 nouveaux tags narratifs de cicatrices"

**Actions** :
1. Génère `alembic/versions/0009_scar_tags_extension.py`.
2. `op.bulk_insert(scar_tags_table, [...50 dicts...])` avec `tag_code` unique.
3. Downgrade : DELETE FROM scar_tags WHERE tag_code IN (...).

---

## Troubleshooting

### Conflit de revision Alembic

**Cause** : 2 migrations avec le même `revision` ou `down_revision`.
**Solution** : renuméroter celle qui n'est pas encore en prod. Toujours faire `alembic heads` pour vérifier.

### Trigger PG bloque migration

**Cause** : on essaie de modifier `base_stats` ou autre colonne immuable.
**Solution** : utiliser session var bypass :
```python
op.execute("SET LOCAL emago.bypass_stats_trigger = 'true'")
op.execute("UPDATE ships SET base_stats = ...")
op.execute("SET LOCAL emago.bypass_stats_trigger = ''")  # reset
```

### FK circulaire échoue

**Cause** : table A référencée avant d'être créée.
**Solution** : utiliser `use_alter=True` sur la FK et créer l'autre table en premier. Cf. alliance ↔ player dans migration 0001.

### Downgrade impossible

**Cause** : migration destructive (DROP COLUMN avec data).
**Solution** : documenter dans le docstring `downgrade()` que les données seront perdues. Toujours faire un backup avant rollback prod.

### `gen_random_uuid()` n'existe pas

**Cause** : extension `pgcrypto` non activée.
**Solution** : ajouter `op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')` au début de la migration (idempotent).

### Index partiel non utilisé par PostgreSQL

**Cause** : la condition WHERE de la query ne matche pas exactement celle de l'index.
**Solution** : `EXPLAIN ANALYZE` pour vérifier ; aligner la condition WHERE de la query avec celle de l'index.

---

## References

- `references/migration_template.py` — template Alembic complet.
- `references/conventions.md` — conventions Emago détaillées (enums, indexes, triggers, FK).
- `references/existing_migrations_summary.md` — résumé des 6 migrations existantes pour réutilisation patterns.
