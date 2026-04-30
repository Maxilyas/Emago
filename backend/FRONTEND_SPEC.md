# Emago — Spécification Frontend complète
> Document destiné à **Agent 6 — Dev Frontend**
> Stack : React 18 + TypeScript + Vite + Tailwind + Zustand + TanStack Query
> Base URL dev : `http://localhost:8000/api/v1`
> WebSocket dev : `ws://localhost:8000/ws?token=<access_token>`

---

## 1. Authentification

### Flux JWT

```
POST /auth/register  →  { access_token, refresh_token, token_type }
POST /auth/login     →  { access_token, refresh_token, token_type }
POST /auth/refresh   →  { access_token, refresh_token, token_type }
```

**Stockage recommandé :** `access_token` en mémoire (Zustand), `refresh_token` en `httpOnly cookie` ou `localStorage` selon votre choix de sécurité. Le `access_token` expire en **60 min**, le `refresh_token` en **30 jours**.

**Header sur chaque requête authentifiée :**
```
Authorization: Bearer <access_token>
```

**Payloads :**

```typescript
// POST /auth/register
interface RegisterRequest {
  username: string;  // 3–32 chars, alphanumérique
  email: string;
  password: string;  // min 8 chars
}

// POST /auth/login
interface LoginRequest {
  email: string;
  password: string;
}

// POST /auth/refresh
interface RefreshRequest {
  refresh_token: string;
}

// Réponse commune
interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}
```

**Codes d'erreur auth :**
| Code | Cas |
|------|-----|
| 409  | Username ou email déjà utilisé (register) |
| 401  | Mauvais identifiants (login) ou token expiré |

---

## 2. Vaisseaux — Hangar

### GET /ships
Liste de tous les vaisseaux du joueur (DOCKED, IN_FLEET, IN_FORGE).

```typescript
interface ShipSummary {
  id: string;           // UUID
  ship_type: string;    // "frigate_attack" | "frigate_defense" | ...
  ship_class: "ATTACK" | "DEFENSE" | "SUPPORT" | "EXPLORATION";
  rarity: "COMMON" | "UNCOMMON" | "RARE" | "EPIC" | "LEGENDARY";
  grade: number;        // 0–5
  status: "DOCKED" | "IN_FLEET" | "IN_FORGE";
  planet_id: string | null;
}
// Réponse : ShipSummary[]
```

### GET /ships/:id
Détail complet avec `current_stats` calculés côté serveur.

```typescript
interface BaseStats {
  hull: number;
  shield: number;
  dps: number;
  speed: number;      // float, 1 décimale
  cargo: number;
  stealth: number;    // float, 0.0–100.0
  support_aura: number; // float, % d'aura
}

interface ModuleDetail {
  slot: number;
  type: "PROPELLER" | "ARMOR" | "CANNON" | "EMITTER" | "SHIELD" | "CARGO";
  level: 1 | 2 | 3 | 4 | 5;
  affinity_bonus: boolean;
  boost_applied: number; // % effectif appliqué
}

interface CurrentStats {
  hull: number;
  shield: number;
  dps: number;
  speed: number;
  cargo: number;
  stealth: number;
  support_aura: number;
  grade: number;
  grade_bonus_pct: number;     // ex: 10.0 pour +10%
  shield_regen_per_round: number; // 0.0 ou 0.02
  cap_reached: string[];        // stats plafonnées à +150% ex: ["dps"]
  modules: ModuleDetail[];
  slots_total: number;
  slots_premium: number;
}

interface ShipDetail {
  id: string;
  ship_type: string;
  ship_class: string;
  rarity: string;
  grade: number;
  combat_xp: number;
  status: string;
  parent_ship_id: string | null;
  base_stats: BaseStats;
  current_stats: CurrentStats;  // NE JAMAIS calculer côté client
}
```

### POST /ships/build
```typescript
// Request
interface BuildShipRequest {
  ship_type: "frigate_attack" | "frigate_defense" | "frigate_support"
           | "frigate_exploration" | "cruiser_attack" | "cruiser_defense";
  planet_id: string;
  parent_ship_id?: string | null;  // Pedigree — vaisseau Grade ≥ 3 du même type
}

// Response 201
interface BuildShipResponse {
  ship_id: string;
  rarity: string;
  ship_class: string;
  base_stats: BaseStats;
  slots_total: number;
  slots_premium: number;
  pedigree_applied: boolean;
}
```

**Codes d'erreur build :**
| Code | Cas |
|------|-----|
| 400  | ship_type inconnu |
| 402  | Ressources insuffisantes sur la planète |
| 404  | Joueur ou planète introuvable |
| 409  | Conditions Pedigree non remplies (grade < 3, mauvais type, non DOCKED) |

### DELETE /ships/:id
Démolition. Retourne **204 No Content**. Erreur 409 si le vaisseau n'est pas DOCKED.

---

## 3. Modules

### GET /ships/:id/modules
```typescript
interface ModuleSlot {
  slot: number;
  type: string;
  level: number;
  affinity_bonus: boolean;
}
// Réponse : ModuleSlot[]
```

### PUT /ships/:id/modules/:slot
```typescript
// Request
interface InstallModuleRequest {
  module_type: "PROPELLER" | "ARMOR" | "CANNON" | "EMITTER" | "SHIELD" | "CARGO";
  level: 1 | 2 | 3 | 4 | 5;
}

// Response 200
interface ModuleInstallResponse {
  current_stats: CurrentStats;
  cap_reached: string[];  // stats ayant atteint le plafond +150%
}
```

**Règles de slots à afficher dans l'UI :**

| Rareté | Slots total | Slots premium |
|--------|-------------|---------------|
| COMMON | 2 | 0 |
| UNCOMMON | 3 | 0 |
| RARE | 4 | 1 |
| EPIC | 5 | 2 |
| LEGENDARY | 6 | 3 |

Les **slots premium** (derniers de la liste) acceptent les modules niveaux IV et V.
Les slots standard n'acceptent que les niveaux I à III.

**Erreurs :**
| Code | Cas |
|------|-----|
| 409  | Vaisseau IN_FORGE |
| 422  | Slot invalide ou module niveau IV/V dans un slot standard |

### DELETE /ships/:id/modules/:slot
Retourne **204 No Content**.

---

## 4. Forge

### POST /forge
```typescript
// Request
interface ForgeStartRequest {
  ship_a_id: string;
  ship_b_id: string;
}

// Response 201
interface ForgeStatusResponse {
  forge_id: string;
  completed_at: string;  // ISO 8601
  progress_pct: number;  // 0–100
  eta_seconds: number;
  result_ship_id?: string | null;
}
```

**Validations côté serveur (afficher message d'erreur correspondant) :**
| Code | Cas |
|------|-----|
| 400  | Même vaisseau deux fois |
| 403  | Un vaisseau appartient à quelqu'un d'autre |
| 404  | Vaisseau introuvable |
| 409  | Un vaisseau n'est pas DOCKED |
| 422  | Types ou raretés différents, ou rareté LEGENDARY (non forgeable) |
| 402  | Ressources insuffisantes (coût = 3× construction du type) |

**Coûts de forge** (3× le coût de construction) :

| Type | Métal | Cristal | Deutérium |
|------|-------|---------|-----------|
| frigate_attack | 9 000 | 3 000 | 0 |
| frigate_defense | 18 000 | 6 000 | 0 |
| frigate_support | 6 000 | 6 000 | 1 500 |
| frigate_exploration | 6 000 | 3 000 | 3 000 |
| cruiser_attack | 60 000 | 21 000 | 6 000 |
| cruiser_defense | 90 000 | 30 000 | 6 000 |

### GET /forge/history
```typescript
interface ForgeHistoryItem {
  forge_id: string;
  ship_a_id: string;
  ship_b_id: string;
  result_ship_id: string | null;
  started_at: string;
  completed_at: string;
  is_completed: boolean;
}
// Réponse : ForgeHistoryItem[] (50 dernières)
```

### GET /forge/:id
Polling fallback — retourne `ForgeStatusResponse`.
**En fonctionnement normal : utiliser le WebSocket `forge.complete` à la place.**

---

## 5. WebSocket

### Connexion
```
ws://localhost:8000/ws?token=<access_token>
```

L'access_token est passé en **query param** (les headers HTTP ne sont pas disponibles lors du handshake WS dans les navigateurs).

### Message de bienvenue (serveur → client, immédiat)
```json
{
  "type": "connected",
  "data": { "player_id": "uuid" }
}
```

### Messages client → serveur

```typescript
// Keepalive
{ "type": "ping" }
// → Réponse : { "type": "pong" }

// Polling forge (fallback si WS interrompu)
{
  "type": "forge.poll",
  "data": { "forge_id": "uuid" }
}
// → Réponse : { "type": "forge.status", "data": ForgeStatusResponse }
```

### Messages serveur → client

#### `forge.complete`
Émis quand la Forge est finalisée par le scheduler (après 8h).
```typescript
interface ForgeCompleteEvent {
  type: "forge.complete";
  data: {
    forge_id: string;
    new_ship_id: string;
    rarity: "UNCOMMON" | "RARE" | "EPIC" | "LEGENDARY";
    base_stats: BaseStats;
    combat_xp: number;
    slots_total: number;
    slots_premium: number;
  };
}
```

#### `combat.result`
Émis après chaque combat (attaquant et défenseur reçoivent chacun cet event).
```typescript
interface CombatResultEvent {
  type: "combat.result";
  data: {
    combat_id: string;
    winner: "ATTACKER" | "DEFENDER" | "DRAW";
    total_rounds: number;
    attacker_power: number;
    defender_power: number;
    ships_lost: {
      attacker: string[];   // UUIDs des vaisseaux détruits
      defender: string[];
    };
    xp_diff: Record<string, number>; // { ship_id: xp_gagnée }
    loot: {
      metal?: number;
      crystal?: number;
      deuterium?: number;
    };
    grade_ups: Array<{
      ship_id: string;
      owner_id: string;
      old_grade: number;
      new_grade: number;
      combat_xp: number;
    }>;
    scars: Array<{
      ship_id: string;
      owner_id: string;
      tag: string;  // ex: "Rescapé de la Nébuleuse Kha"
    }>;
    synergies: {
      attacker: string[];  // descriptions textuelles des synergies actives
      defender: string[];
    };
  };
}
```

#### `ship.grade_up`
```typescript
interface ShipGradeUpEvent {
  type: "ship.grade_up";
  data: {
    ship_id: string;
    owner_id: string;
    old_grade: number;
    new_grade: number;
    combat_xp: number;
  };
}
```

#### `ship.scar_earned`
```typescript
interface ShipScarEarnedEvent {
  type: "ship.scar_earned";
  data: {
    ship_id: string;
    owner_id: string;
    tag: string;  // tag narratif aléatoire
  };
}
```

#### `fleet.arrived`
```typescript
interface FleetArrivedEvent {
  type: "fleet.arrived";
  data: {
    fleet_id: string;
    mission: "ATTACK" | "TRANSPORT" | "ESPIONAGE" | "COLONIZE" | "RECALL";
    target_planet_id: string | null;
  };
}
```

### Reconnexion WebSocket
Le client doit implémenter une reconnexion automatique avec backoff exponentiel.
En cas de déconnexion pendant une forge active, utiliser `GET /forge/:id` comme fallback.

---

## 6. Palette de rareté (identité visuelle)

| Rareté | Couleur | Hex | Usage |
|--------|---------|-----|-------|
| COMMON | Gris | `#9E9E9E` | Bordure, badge, texte |
| UNCOMMON | Vert | `#4CAF50` | Bordure, badge, texte |
| RARE | Bleu | `#2196F3` | Bordure, badge, texte |
| EPIC | Violet | `#9C27B0` | Bordure, badge, texte |
| LEGENDARY | Or | `#FFD700` | Bordure + effet lumineux subtil |

La rareté est toujours lue depuis le champ `rarity` retourné par l'API. **Jamais calculée côté client.**

---

## 7. Grades — informations affichage

| Grade | Nom | XP requise | Bonus affiché |
|-------|-----|------------|---------------|
| 0 | Recrue | 0 | — |
| 1 | Vétéran | 500 | +5% toutes stats |
| 2 | Élite | 2 000 | +10% toutes stats, +1 slot |
| 3 | Légion | 6 000 | +15% toutes stats, régén. bouclier 2%/round |
| 4 | Légende | 15 000 | +22% toutes stats, immunité 1re mort |
| 5 | Spectre | 40 000 | +30% toutes stats, +1 slot premium, furtivité +10% |

---

## 8. Types de vaisseaux — configuration UI

| ship_type | Classe | Icône suggérée |
|-----------|--------|----------------|
| frigate_attack | ATTACK | ⚔️ |
| frigate_defense | DEFENSE | 🛡️ |
| frigate_support | SUPPORT | 💊 |
| frigate_exploration | EXPLORATION | 🔭 |
| cruiser_attack | ATTACK | ⚔️ |
| cruiser_defense | DEFENSE | 🛡️ |

---

## 9. Modules — référence

| module_type | Stat boostée | Affinité classe | Niveaux I/V en % |
|-------------|--------------|-----------------|------------------|
| PROPELLER | speed | EXPLORATION | 8 / 44 % (×1.15 avec affinité) |
| ARMOR | hull | DEFENSE | 8 / 44 % |
| CANNON | dps | ATTACK | 8 / 44 % |
| EMITTER | support_aura | SUPPORT | 8 / 44 % |
| SHIELD | shield | DEFENSE | 8 / 44 % |
| CARGO | cargo | EXPLORATION | 8 / 44 % |

Les boosts **avec affinité** sont multipliés par ×1.15 (ex: +8% → +9.2%).

---

## 10. Recommandations d'implémentation

### Hook WebSocket (exemple skeleton)
```typescript
// hooks/useGameSocket.ts
const useGameSocket = () => {
  const { accessToken } = useAuthStore();

  useEffect(() => {
    if (!accessToken) return;
    const ws = new WebSocket(`ws://localhost:8000/ws?token=${accessToken}`);

    ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      switch (event.type) {
        case "combat.result":   handleCombatResult(event.data); break;
        case "forge.complete":  handleForgeComplete(event.data); break;
        case "ship.grade_up":   handleGradeUp(event.data); break;
        case "ship.scar_earned":handleScarEarned(event.data); break;
        case "fleet.arrived":   handleFleetArrived(event.data); break;
      }
    };

    // Reconnexion avec backoff
    ws.onclose = () => setTimeout(() => reconnect(), Math.min(delay * 2, 30000));
    return () => ws.close();
  }, [accessToken]);
};
```

### Règles absolues
1. **`current_stats` n'est JAMAIS calculé côté client.** Toujours utiliser ce que retourne `GET /ships/:id`.
2. **Après un event WS `combat.result` ou `forge.complete`**, invalider les queries TanStack concernées pour forcer un refetch.
3. **La rareté est lue depuis l'API**, jamais inférée depuis d'autres champs.
4. **Les countdowns de forge** s'interpolent côté client (`eta_seconds` → timer local) mais `GET /forge/:id` reste la source de vérité.
5. **`cap_reached`** : si une stat est dans ce tableau, afficher un indicateur visuel (ex: icône 🔒 ou bordure rouge) pour informer que le cap +150% est atteint.

### Gestion d'erreur recommandée
```typescript
// Intercepteur axios/fetch recommandé
if (response.status === 401) {
  // Token expiré → refresh automatique via POST /auth/refresh
  // Si le refresh échoue → logout
}
if (response.status === 402) {
  // Ressources insuffisantes → afficher le message du serveur
  // response.data.detail contient le détail (requis vs disponible)
}
```

---

## 11. Endpoints manquants (phase 2 — pas encore implémentés)

Ces endpoints seront disponibles dans la prochaine livraison Agent 5 :
- `GET /planets` — liste des planètes du joueur
- `GET /planets/:id` — détail planète + ressources actuelles + taux de production
- `POST /fleets` — envoyer une flotte
- `DELETE /fleets/:id` — rappeler une flotte
- `GET /combat/:id` — rapport de combat complet
- `GET /ranking` — classement des joueurs
- `GET /ships/:id/scars` — cicatrices d'un vaisseau
- `GET /ships/:id/missions` — missions actives (grade ≥ 2)

**Pour la planification UI :** prévoir les écrans correspondants mais ne pas les relier à l'API avant la livraison.
