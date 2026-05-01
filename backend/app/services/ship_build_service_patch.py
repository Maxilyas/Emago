"""
PATCH ship_build_service.py — v1.1
Agent 5 — Sprint RPG

MODIFICATIONS par rapport à la version actuelle :
  1. Import ship_trait_service.roll_trait()
  2. Import naming_service.generate_ship_name()
  3. Dans build_ship() : tirage du trait + génération du nom après le RNG rareté
  4. Le Ship() INSERT passe les champs trait= et name=

ATTENTION : Ces champs (trait, name, is_drift) doivent être ajoutés au
modèle Ship et à la migration 0006 (Agent 7) avant d'appliquer ce patch.

Application : remplacer les sections marquées dans ship_build_service.py
existant. Les autres sections restent identiques.
"""

# ─── Section à ajouter dans les imports (après les imports existants) ────────

# from app.services.ship_trait_service import roll_trait
# from app.services.naming_service import generate_ship_name


# ─── Section à remplacer dans build_ship() ───────────────────────────────────
# Repérer le bloc "# 3. RNG" et remplacer par :

PATCH_BUILD_SHIP_RNG_BLOCK = '''
    # 3. RNG — rareté, stats, trait narratif, nom procédural
    rarity     = roll_rarity()
    base_stats = generate_base_stats(ship_class, rarity)
    trait      = roll_trait()                              # ← NOUVEAU
    ship_name  = generate_ship_name(ship_class, rarity)   # ← NOUVEAU (None si COMMON/UNCOMMON)
'''

# ─── Section à remplacer dans le Ship() INSERT ───────────────────────────────
# Repérer le bloc "ship = Ship(" et ajouter les deux champs :

PATCH_SHIP_INSERT = '''
    ship = Ship(
        owner_id=player_id,
        planet_id=planet_id,
        ship_type=ship_type,
        class_=ShipClass(ship_class),
        rarity=ShipRarity(rarity),
        grade=0,
        combat_xp=0,
        base_stats=base_stats,
        parent_ship_id=parent_id_to_store,
        status=ShipStatus.DOCKED,
        trait=trait,           # ← NOUVEAU : {"key": ..., "name": ..., "description": ...}
        name=ship_name,        # ← NOUVEAU : "Astraeus Noir" ou None
        is_drift=False,        # ← NOUVEAU : False par défaut (True uniquement via Forge)
    )
'''

# ─── Réponse build ship (router ships.py) ────────────────────────────────────
# Ajouter dans BuildShipResponse les nouveaux champs :

PATCH_BUILD_SHIP_RESPONSE = '''
# Dans routers/ships.py — BuildShipResponse :
class BuildShipResponse(BaseModel):
    ship_id: uuid.UUID
    rarity: str
    ship_class: str
    base_stats: dict
    slots_total: int
    slots_premium: int
    pedigree_applied: bool
    trait: dict          # ← NOUVEAU {"key", "name", "description"}
    name: str | None     # ← NOUVEAU "Astraeus Noir" ou None
    is_drift: bool       # ← NOUVEAU toujours False à la construction normale

# Et dans le return du router :
    return BuildShipResponse(
        ship_id=ship.id,
        rarity=_enum_val(ship.rarity),
        ship_class=_enum_val(ship.class_),
        base_stats=ship.base_stats,
        slots_total=total_slots,
        slots_premium=premium_slots,
        pedigree_applied=parent_ship_id is not None,
        trait=ship.trait,           # ← NOUVEAU
        name=ship.name,             # ← NOUVEAU
        is_drift=ship.is_drift,     # ← NOUVEAU
    )
'''

# ─── Instructions d'application complètes ────────────────────────────────────
APPLY_INSTRUCTIONS = """
ORDRE D'APPLICATION :

1. Agent 7 applique migration 0006 (champs ships.trait, ships.name, ships.is_drift)
2. Agent 7 met à jour le modèle SQLAlchemy Ship (models.py)
3. Agent 5 applique ce patch dans ship_build_service.py et ships.py

Vérification post-patch :
  - POST /ships/build retourne {ship_id, rarity, ..., trait, name, is_drift}
  - Un COMMON a name=null, trait avec key+name+description
  - Un LEGENDARY a un nom du type "Astraeus Noir"
  - Tests : pytest tests/services/test_ship_services.py -k "trait or name"
"""

if __name__ == "__main__":
    print(APPLY_INSTRUCTIONS)
    print("\n--- PATCH RNG BLOCK ---")
    print(PATCH_BUILD_SHIP_RNG_BLOCK)
    print("\n--- PATCH SHIP INSERT ---")
    print(PATCH_SHIP_INSERT)
    print("\n--- PATCH RESPONSE ---")
    print(PATCH_BUILD_SHIP_RESPONSE)
