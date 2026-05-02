# Codes d'erreur HTTP Emago — convention

## Tableau récapitulatif

| Code | Sémantique Emago | Exemples de message FR |
|---:|---|---|
| **200** | OK | (response normale) |
| **201** | Créé | response avec id du nouvel objet |
| **204** | No Content | DELETE réussi (pas de body) |
| **400** | Donnée invalide | `"Mission invalide : XXXXX. Valeurs : ATTACK, TRANSPORT, ESPIONAGE, COLONIZE"` |
| **401** | Auth manquante / invalide | `"Email ou mot de passe incorrect."` (anti-énumération login) |
| **402** | Ressources insuffisantes | `"Ressources insuffisantes. Requis : métal=10000, cristal=5000. Disponible : métal=3500, cristal=2000."` |
| **403** | Refus explicite | `"Rôle insuffisant pour cette action."`, `"Le vaisseau {id} ne vous appartient pas."` |
| **404** | Introuvable OU ownership masqué | `"Vaisseau introuvable."`, `"Planète introuvable."` |
| **409** | Conflit d'état | `"Vaisseau IN_FORGE."`, `"Cette alliance est complète (20 membres max)."`, `"Une recherche est déjà en cours."` |
| **422** | Validation | Auto Pydantic OU `"Module niveau IV/V réservé aux slots premium."` |
| **429** | Rate-limit | (avec header `Retry-After: 60`) |
| **500** | Erreur serveur | (rollback automatique) |
| **503** | Dégradé | (sur /health uniquement, retour DB ou Redis KO) |

## Quand utiliser 404 vs 403

| Cas | Code |
|---|---:|
| GET ship d'autrui | **404** (anti-énumération — ne pas révéler existence) |
| GET planet d'autrui via ID | **404** |
| DELETE ship d'autrui | **404** |
| PUT modules sur ship d'autrui | **404** |
| Forge avec ship_b d'autrui (ID fourni explicit) | **403** (user a forni l'ID, donc il sait qu'il existe) |
| Pedigree avec parent d'autrui (ID explicit) | **403** |
| Action alliance sans rôle suffisant | **403** |
| GET ranking (public) | (200) |
| GET alliances list (public) | (200) |

## Messages français — convention

### Toujours en français
Tous les messages d'erreur user-facing sont en français. Pas d'anglais.

### Format détaillé pour 402

```python
raise HTTPException(
    status_code=402,
    detail=(
        f"Ressources insuffisantes. "
        f"Requis : métal={cost['metal']}, cristal={cost['crystal']}, deutérium={cost['deuterium']}. "
        f"Disponible : métal={floor(planet.metal)}, cristal={floor(planet.crystal)}, deutérium={floor(planet.deuterium)}."
    )
)
```

### Format pour 409 statut bloquant

```python
raise HTTPException(
    status_code=409,
    detail=f"Impossible de démolir un vaisseau {ship.status.value}."
)
```

### Format pour 422 contrainte business

```python
raise HTTPException(
    status_code=422,
    detail=f"Slot {slot_index} invalide pour rareté {ship.rarity.value} (max {total_slots})."
)
```

### Format pour 404 (anti-énumération)

```python
# TOUJOURS le même message générique pour ne pas révéler l'existence
raise HTTPException(status_code=404, detail="Vaisseau introuvable.")
raise HTTPException(status_code=404, detail="Planète introuvable.")
raise HTTPException(status_code=404, detail="Forge introuvable.")
raise HTTPException(status_code=404, detail="Alliance introuvable.")
```

## Anti-patterns à éviter

### ❌ Message en anglais
```python
raise HTTPException(status_code=409, detail="Ship cannot be destroyed in fleet")
```

### ❌ Détail technique exposé
```python
raise HTTPException(status_code=500, detail=str(e))  # peut leak SQL/stack
```

### ❌ 403 quand 404 conviendrait
```python
# MAUVAIS : révèle que la ressource existe
if ship.owner_id != player.id:
    raise HTTPException(status_code=403, detail="Pas votre vaisseau")

# BON
if ship.owner_id != player.id:
    raise HTTPException(status_code=404, detail="Vaisseau introuvable.")
```

### ❌ Message vague pour 402
```python
raise HTTPException(status_code=402, detail="Pas assez de ressources")  # frustrant pour l'utilisateur
```

### ❌ Different messages pour login email inconnu vs mauvais MDP
```python
# MAUVAIS : permet l'énumération de comptes
if not user:
    raise HTTPException(401, "Email inconnu")
if not check_password(password):
    raise HTTPException(401, "Mauvais mot de passe")

# BON : message unique
if not user or not check_password(password):
    raise HTTPException(401, "Email ou mot de passe incorrect.")
```

## Codes spécifiques Emago

### `_LIMITS` rate-limit (60s sliding window)

```python
# app/middleware/rate_limit.py _LIMITS
"ships:build": 10
"forge:start": 5
"fleets:send": 20
"auth:register": 5
"auth:login": 10
"modules:install": 30
"default": 120
```

Pour ajouter un nouveau tag :
```python
_LIMITS["espionage:probe"] = 5
```

Puis dans le router :
```python
from app.middleware.rate_limit import check_rate_limit

@router.post("/probe", status_code=201)
async def launch_probe(...):
    await check_rate_limit(player.id, "espionage:probe")
    # ...
```

## Convention de logs (en cas de raise)

Les `HTTPException` ne sont pas loguées par défaut. Si besoin d'audit :

```python
import logging
logger = logging.getLogger(__name__)

if some_anomaly:
    logger.warning(f"Tentative {action} par {player.id} sur ressource d'autrui {resource_id}")
    raise HTTPException(status_code=404, detail="...")  # masqué pour l'utilisateur
```

Cela permet de détecter les patterns d'attaque côté serveur sans révéler info au client.
