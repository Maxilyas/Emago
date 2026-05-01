"""
app/services/naming_service.py
Agent 5 — Développeur Backend

Responsabilité : Génération procédurale de noms pour les vaisseaux RARE+.

Les vaisseaux RARE, EPIC et LEGENDARY reçoivent un nom unique à la
construction. Les COMMON et UNCOMMON n'ont pas de nom (ships.name = NULL).

Format du nom : [Adjectif] [Nom propre spatial]
Exemples : "Astraeus Noir", "Corvus Prime", "Vael Silencieux", "Dernier Eryndor"

Les noms sont composés de deux parties tirées indépendamment :
  - Une racine spatiale (nom propre fictif ou référence cosmique)
  - Un qualificatif contextuel lié à la classe du vaisseau

Le nom est stocké dans ships.name (VARCHAR 64, nullable).
Il est immuable après création (comme base_stats).
"""
from __future__ import annotations

import secrets

# ---------------------------------------------------------------------------
# Racines spatiales — 80 noms propres fictifs
# ---------------------------------------------------------------------------

_ROOTS: list[str] = [
    # Nébuleuses & Systèmes
    "Astraeus", "Corvus", "Vael", "Eryndor", "Kha", "Fenrath", "Obsidia",
    "Arcturus", "Veloris", "Noctara", "Pyreth", "Solux", "Umbrath", "Zephyr",
    "Caelum", "Dravon", "Elsyn", "Fyranthos", "Garath", "Helyx",
    # Étoiles mortes & Restes
    "Ignar", "Jorth", "Kalyx", "Lyrath", "Merrak", "Nexis", "Orvath",
    "Praxis", "Queth", "Rylos", "Sythren", "Thalos", "Ulvex", "Vandris",
    "Wrakon", "Xanthos", "Yldra", "Zorah", "Aevon", "Brakthos",
    # Constellations oubliées
    "Cyrix", "Dalveth", "Elmarion", "Frakast", "Grevyx", "Hyloth", "Ixar",
    "Jarveth", "Keldris", "Lyvorn", "Myrath", "Noldras", "Orexis", "Pelvor",
    "Quarthos", "Ralkyn", "Seldris", "Tyrvox", "Ulnarath", "Voryx",
    # Anciens dieux & Entités
    "Ashkarath", "Belnor", "Caldrixis", "Drevakos", "Ethyran", "Felvaris",
    "Grethon", "Hylakon", "Iryvex", "Jarakhon", "Keldrion", "Lorethax",
    "Mavrik", "Neldrath", "Orthax", "Pyraxis", "Queldrith", "Rethvaris",
    "Selvion", "Tharkon",
]

# ---------------------------------------------------------------------------
# Qualificatifs par classe de vaisseau
# ---------------------------------------------------------------------------

_QUALIFIERS: dict[str, list[str]] = {
    "ATTACK": [
        "Noir", "Rouge", "de Fer", "Brisé", "Furieux", "Sanglant",
        "Impitoyable", "Ardent", "Vengeur", "Implacable",
        "de Guerre", "Corrosif", "Silencieux", "Brutal", "Écarlate",
    ],
    "DEFENSE": [
        "Inébranlable", "Éternel", "de Granit", "Immuable", "Solide",
        "Stoïque", "de Pierre", "Indompté", "Massif", "Invaincu",
        "Forteresse", "Blindé", "Indestructible", "Robuste", "Inflexible",
    ],
    "SUPPORT": [
        "Lumineux", "Gardien", "Bienveillant", "de Lumière", "Sage",
        "Harmonieux", "Protecteur", "Guérisseur", "Serein", "Altruiste",
        "Radieux", "Porteur", "Fidèle", "Vigile", "Sanctifié",
    ],
    "EXPLORATION": [
        "Prime", "Errant", "Libre", "Fantôme", "de l'Abysse", "Solitaire",
        "Perdu", "Silencieux", "de l'Ombre", "Immortel",
        "Nomade", "Fugace", "Invisible", "Lointain", "Pionnier",
    ],
}

# Qualificatifs génériques pour les cas imprévus
_GENERIC_QUALIFIERS: list[str] = [
    "Ancien", "Dernier", "Premier", "Ultime", "Oublié", "Légendaire",
    "Mystérieux", "Redoutable", "Obscur", "Glorieux",
]

# Singleton SystemRandom
_srng = secrets.SystemRandom()


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

# Raretés qui reçoivent un nom
_NAMED_RARITIES = {"RARE", "EPIC", "LEGENDARY"}


def generate_ship_name(ship_class: str, rarity: str) -> str | None:
    """
    Génère un nom procédural pour les vaisseaux RARE+.
    Retourne None pour les raretés inférieures.

    Args:
        ship_class : "ATTACK" | "DEFENSE" | "SUPPORT" | "EXPLORATION"
        rarity     : "COMMON" | "UNCOMMON" | "RARE" | "EPIC" | "LEGENDARY"

    Returns:
        Nom du vaisseau (ex: "Astraeus Noir") ou None.
    """
    if rarity not in _NAMED_RARITIES:
        return None

    root = _srng.choice(_ROOTS)
    qualifiers = _QUALIFIERS.get(ship_class, _GENERIC_QUALIFIERS)
    qualifier = _srng.choice(qualifiers)

    return f"{root} {qualifier}"
