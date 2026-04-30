---
HANDOFF EMAGO
De : Agent 3 — Architecte système
À : Agent 5 — Développeur Backend / Agent 7 — Développeur Base de données
Sujet : Architecture complète du système de vaisseaux
Date : 2025-01-29
---

### Contexte reçu
GDD v1.0 du système de vaisseaux (Agent 2) : classes, rareté RNG,
modules, XP/grades, Pedigree, Forge, Missions, Cicatrices.
Objectif : concevoir l'architecture technique complète qui implémente
ce GDD de façon sécurisée, scalable et cohérente avec la stack.

### Décisions prises

**1. Séparation stricte routers / services**
Aucune logique métier dans les routers FastAPI. Chaque router délègue
immédiatement à son service. Raison : testabilité et évolution sans
toucher à l'API publique.

**2. `current_stats` n'est jamais stocké en base**
Il est calculé à la volée par `ship_stats_service` et mis en cache Redis.
Stocker `current_stats` en base créerait des inconsistances à chaque
modification de module ou montée de grade. Redis avec TTL 5min et
invalidation sur mutation est le bon compromis.

**3. Trigger PostgreSQL sur `base_stats`**
Un trigger `BEFORE UPDATE` lève une exception si `NEW.base_stats !=
OLD.base_stats`. C'est la seule garantie fiable d'immuabilité — une
contrainte applicative seule ne suffit pas face à des bugs futurs ou
des accès directs en base.

**4. `SystemRandom` pour le RNG, pas `random`**
Le module `random` de Python est seedable et potentiellement prédictible.
`secrets.SystemRandom()` utilise l'entropie du système d'exploitation.
Les stats RNG doivent être générées en une seule passe et stockées
immédiatement dans `base_stats`.

**5. Forge asynchrone via scheduler**
La Forge dure 8h. APScheduler vérifie `forge_queue` toutes les minutes
et déclenche la finalisation quand `completed_at <= now()`. Pas de
Celery pour ce volume — sur-ingénierie. Redis stocke la progression
pour le polling client toutes les 30 secondes.

**6. WebSocket pour XP post-combat uniquement**
Le résultat de combat est d'abord écrit en base (transaction ACID),
puis le serveur émet un event WS `combat.result` vers les joueurs
concernés. Le client ne calcule rien — il reçoit le diff de stats.

---

### Livrable
```

---

## Architecture proposée

```
Client React
     │
     ├── REST (TanStack Query)
     └── WebSocket (hook custom)
          │
    Nginx (reverse proxy, SSL, upgrade WS)
          │
    FastAPI (Uvicorn, async)
     ├── /routers/ships.py       ──► ship_build_service
     ├── /routers/modules.py     ──► ship_stats_service
     ├── /routers/forge.py       ──► forge_service
     ├── /routers/combat.py      ──► combat_engine
     └── /websocket/handler.py
          │
     /services/
     ├── ship_build_service.py   (RNG, rareté, Pedigree)
     ├── ship_stats_service.py   (current_stats, cap +150%)
     ├── combat_engine.py        (rounds, synergies, XP diff.)
     └── forge_service.py        (fusion, scheduler)
          │
     ┌────────────────────┐
     │   PostgreSQL 16    │   ←→   Redis 7
     └────────────────────┘
```

---

## Endpoints API REST

### Hangar

| Méthode | Path | Description | Auth |
|---|---|---|---|
| `GET` | `/ships` | Liste des vaisseaux du joueur (depuis Redis si chaud) | JWT |
| `GET` | `/ships/{id}` | Détail complet : base_stats + current_stats + modules + grades | JWT |
| `POST` | `/ships/build` | Lance la fabrication d'un vaisseau (déduit ressources, tire RNG) | JWT |
| `DELETE` | `/ships/{id}` | Démolition volontaire (déclenche Pedigree si Grade ≥ 3) | JWT |

**`POST /ships/build` — payload :**
```json
{
  "ship_type": "frigate_attack",
  "planet_id": "uuid"
}
```

**`POST /ships/build` — response :**
```json
{
  "ship_id": "uuid",
  "rarity": "RARE",
  "class": "ATTACK",
  "base_stats": { "hull": 152, "shield": 31, "dps": 79, "speed": 44, "cargo": 198, "stealth": 0 },
  "slots": 4,
  "premium_slots": 1,
  "pedigree": null
}
```

### Modules (loadout)

| Méthode | Path | Description |
|---|---|---|
| `GET` | `/ships/{id}/modules` | Liste des modules installés par slot |
| `PUT` | `/ships/{id}/modules/{slot}` | Installe ou remplace un module |
| `DELETE` | `/ships/{id}/modules/{slot}` | Retire un module (récupère l'objet) |

**Validation côté serveur obligatoire :**
- Le slot existe pour la rareté du vaisseau
- Le niveau du module est compatible avec le type de slot (standard vs premium)
- Le joueur possède le module
- La stat résultante ne dépasse pas le cap +150%

**`PUT /ships/{id}/modules/{slot}` — response :**
```json
{
  "current_stats": { "hull": 198, "shield": 31, "dps": 110, "speed": 44 },
  "modules": [
    { "slot": 0, "type": "CANNON", "level": 3, "affinity_bonus": true }
  ],
  "cap_reached": ["dps"]
}
```

### Forge

| Méthode | Path | Description |
|---|---|---|
| `POST` | `/forge` | Lance une fusion (vérifie type + rareté identiques) |
| `GET` | `/forge/{id}` | Statut de la forge en cours (depuis Redis) |
| `GET` | `/forge/history` | Historique des fusions du joueur |

**`POST /forge` — payload :**
```json
{
  "ship_a_id": "uuid",
  "ship_b_id": "uuid"
}
```

**Validation serveur :**
- Même `ship_type` strict
- Même `rarity`
- Les deux vaisseaux appartiennent au joueur
- Aucun des deux n'est en déplacement de flotte
- Ressources suffisantes (≡ 3× coût de construction du type)

### Cicatrices & Missions

| Méthode | Path | Description |
|---|---|---|
| `GET` | `/ships/{id}/scars` | Liste des cicatrices narratives |
| `GET` | `/ships/{id}/missions` | Missions actives (Grade ≥ 2 requis) |
| `POST` | `/ships/{id}/missions/{mission_id}/claim` | Réclame récompense (skin, titre) |

---

## Événements WebSocket

### Serveur → Client

| Event | Déclencheur | Payload clé |
|---|---|---|
| `ship.built` | Fin de construction | `{ ship_id, rarity, base_stats }` |
| `ship.grade_up` | Seuil XP franchi | `{ ship_id, new_grade, bonus_passive }` |
| `ship.scar_earned` | Combat difficile survécu | `{ ship_id, scar_tag, narrative }` |
| `forge.complete` | Scheduler finalise la forge | `{ new_ship_id, rarity, base_stats }` |
| `combat.result` | Combat résolu | `{ combat_id, outcome, xp_diff, ships_lost }` |
| `mission.available` | Nouvelle mission générée | `{ ship_id, mission_type, expires_at }` |

### Client → Serveur

| Event | Usage |
|---|---|
| `fleet.subscribe` | S'abonner aux mises à jour d'une flotte |
| `forge.poll` | Demande de refresh du statut forge (fallback si WS interrompu) |

---

## Schéma de données (résumé pour Agent 7)

### Table `ships`

```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
owner_id        UUID NOT NULL REFERENCES players(id)
ship_type       VARCHAR(64) NOT NULL          -- ex: "frigate_attack"
class           ship_class NOT NULL           -- enum ATTACK|DEFENSE|SUPPORT|EXPLORATION
rarity          ship_rarity NOT NULL          -- enum COMMON|UNCOMMON|RARE|EPIC|LEGENDARY
grade           SMALLINT NOT NULL DEFAULT 0   -- 0–5
combat_xp       INTEGER NOT NULL DEFAULT 0
base_stats      JSONB NOT NULL                -- IMMUABLE — trigger BEFORE UPDATE
parent_ship_id  UUID REFERENCES ships(id)     -- Pedigree nullable
status          ship_status NOT NULL DEFAULT 'DOCKED'  -- DOCKED|IN_FLEET|IN_FORGE
created_at      TIMESTAMPTZ DEFAULT now()
```

`current_stats` : **jamais en base**. Calculé par `ship_stats_service`, stocké dans Redis avec clé `ship:{id}:stats`, TTL 5 minutes, invalidé sur toute modification du loadout ou changement de grade.

### Table `ship_modules`

```sql
id          UUID PRIMARY KEY
ship_id     UUID NOT NULL REFERENCES ships(id) ON DELETE CASCADE
slot_index  SMALLINT NOT NULL
module_type module_family NOT NULL   -- enum PROPELLER|ARMOR|CANNON|EMITTER|SHIELD|CARGO
level       SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 5)
UNIQUE (ship_id, slot_index)
```

### Table `forge_queue`

```sql
id          UUID PRIMARY KEY
ship_a_id   UUID NOT NULL REFERENCES ships(id)
ship_b_id   UUID NOT NULL REFERENCES ships(id)
player_id   UUID NOT NULL REFERENCES players(id)
started_at  TIMESTAMPTZ NOT NULL DEFAULT now()
completed_at TIMESTAMPTZ NOT NULL   -- INDEX obligatoire pour le scheduler
result_ship_id UUID REFERENCES ships(id)  -- NULL jusqu'à finalisation
```

### Table `ship_scars`

```sql
id        UUID PRIMARY KEY
ship_id   UUID NOT NULL REFERENCES ships(id) ON DELETE CASCADE
tag_id    INTEGER NOT NULL   -- FK vers table scar_tags (pool ~500 tags)
earned_at TIMESTAMPTZ DEFAULT now()
```

### Table `ship_missions`

```sql
id          UUID PRIMARY KEY
ship_id     UUID NOT NULL REFERENCES ships(id) ON DELETE CASCADE
type        VARCHAR(64) NOT NULL
condition   JSONB NOT NULL    -- ex: { "kills": 10, "ship_class": "FRIGATE" }
progress    JSONB NOT NULL DEFAULT '{}'
reward      JSONB NOT NULL    -- ex: { "skin": "nova_red" }
expires_at  TIMESTAMPTZ NOT NULL  -- renouvellement toutes les 72h
completed   BOOLEAN NOT NULL DEFAULT FALSE
```

---

## Stratégie Redis

| Clé | Contenu | TTL | Invalidation |
|---|---|---|---|
| `ship:{id}:stats` | `current_stats` JSON complet | 5 min | PUT /modules, grade_up |
| `player:{id}:hangar` | Liste `[{id, rarity, class, grade, status}]` | 2 min | build, demolish, forge |
| `forge:{id}:status` | `{progress_pct, eta_seconds}` | Durée de la forge | Completion ou annulation |
| `combat:{id}:result` | Rapport complet sérialisé | 10 min | Jamais (lecture seule) |

---

## Décisions techniques

**Pas de `current_stats` en base.** Alternative écartée : colonne JSONB mise à jour à chaque modification. Risque : update manqué = stats incorrectes. Avec Redis + calcul à la demande, la source de vérité reste toujours `base_stats + ship_modules`.

**APScheduler pour la Forge, pas Celery.** Alternative écartée : Celery + Redis broker. Sur-ingénierie pour un volume de quelques dizaines de joueurs. APScheduler dans le processus FastAPI suffit, avec une tâche toutes les 60 secondes. Si le projet scale à 10 000 joueurs, Celery s'ajoutera sans refonte.

**Trigger PostgreSQL pour l'immuabilité de `base_stats`.** Alternative écartée : validation uniquement applicative dans `ship_build_service`. Un bug, une migration mal écrite ou un accès DBA direct pourraient corrompre les stats. Le trigger est la seule garantie vraiment fiable.

**`ship.status` enum dans `ships`.** Alternative écartée : vérifications ad hoc dans chaque service. L'état `IN_FLEET`, `IN_FORGE`, `DOCKED` est vérifié à plusieurs endroits (forge, déploiement de flotte, démolition). Un champ centralisé évite les race conditions et simplifie les guards.

---

## Points de vigilance pour les agents

**Pour Agent 5 (Backend) :**
- Toute opération qui consomme des ressources ET modifie `ships` doit être dans une seule transaction PostgreSQL avec `SELECT ... FOR UPDATE` sur la ligne joueur.
- `ship_stats_service.get_current_stats(ship_id)` doit être la seule fonction qui calcule `current_stats`. Elle lit Redis d'abord, recalcule si absent, invalide toujours après mutation.
- La formule XP différentielle (`XP_gagnée = base_XP × (1 + max(0, puissance_ennemie / puissance_propre - 1) × 2.5)`) doit être loggée avec ses paramètres dans `combat_logs` pour auditabilité.
- Le cap +150% par stat est vérifié dans `ship_stats_service` ET renvoyé dans la response du PUT /modules (champ `cap_reached`) pour que l'UI puisse informer le joueur.

**Pour Agent 7 (Base de données) :**
- Index obligatoire sur `forge_queue.completed_at` (utilisé toutes les 60 secondes par le scheduler).
- Index sur `ships.owner_id` + `ships.status` (requête la plus fréquente : hangar actif d'un joueur).
- Index sur `ship_modules.ship_id` (requête systématique au calcul de `current_stats`).
- Le trigger BEFORE UPDATE sur `ships` doit aussi couvrir les UPDATE en masse (migrations Alembic) — prévoir un flag `BYPASS_STATS_TRIGGER` en variable de session pour les migrations contrôlées.
- Enums PostgreSQL requis : `ship_class`, `ship_rarity`, `ship_status`, `module_family`.

**Pour Agent 6 (Frontend) :**
- Le client ne doit jamais calculer `current_stats`. Il affiche ce que le serveur renvoie. L'interpolation locale (animations de stats qui montent) est cosmétique — le prochain GET /ships/{id} est la vérité.
- Le polling forge via `GET /forge/{id}` toutes les 30 secondes est le fallback si le WebSocket est déconnecté. En fonctionnement normal, `forge.complete` via WS suffit.
- La rareté doit être lue depuis `base_stats.rarity` retourné par l'API — jamais inférée côté client.

**Pour Agent 8 (QA & Sécurité) :**
- Vecteur critique : un joueur envoie `PUT /ships/{id}/modules/{slot}` avec un `ship_id` qui appartient à un autre joueur. Le router doit vérifier `ship.owner_id == jwt.player_id` avant toute opération.
- Vecteur critique : double-soumission de `/forge` avant que le status passe à `IN_FORGE`. Utiliser une transaction avec `SELECT ... FOR UPDATE` sur les deux lignes vaisseaux + vérification du statut dans la même transaction.
- À tester : un vaisseau `IN_FLEET` ne peut pas être envoyé en forge (guard sur `ship.status`).

---

### Prochaine étape suggérée

**Agent 7** peut maintenant écrire le schéma SQL complet avec migrations Alembic, triggers et index.
**Agent 5** peut commencer `ship_build_service.py` et `ship_stats_service.py` dès réception du schéma Agent 7.
**Agent 6** peut commencer `<ShipCard />` et `<HangarList />` sur la base des payloads API définis ici.

---