"""
app/services/ship_trait_service.py
Agent 5 — Développeur Backend

Responsabilité : Traits narratifs de vaisseaux.

Chaque vaisseau reçoit UN trait unique à la construction (tiré au RNG,
indépendant de la rareté). Un trait combine :
  - Un libellé narratif affiché dans le hangar
  - Un effet mécanique mineur conditionnel (±5-10% sur une stat, selon contexte)
  - Une condition d'activation (SOLO, FLEET, CLASS_BONUS)

GDD créatif (Agent 2) :
  - "Chasseur de Primes" : +10% DPS si combat en solo (sans alliés dans la flotte)
  - "Âme de Navigateur"  : +15% vitesse si flotte mono-vaisseau
  - "Âme d'Équipage"     : +8% toutes stats si ≥ 3 alliés dans la flotte
  - etc.

Architecture (Agent 3) :
  - Les traits sont stockés en JSONB dans ships.trait (clé + nom + description)
  - L'effet mécanique est appliqué dans combat_engine au calcul des synergies
  - Le trait est tiré une seule fois à la construction (immuable comme base_stats)
  - Pas de table BDD externe : pool en mémoire + clé stockée dans le JSONB ship

Format stocké dans ships.trait :
    {"key": "bounty_hunter", "name": "Chasseur de Primes", "description": "..."}

L'effet est résolu à l'exécution via TRAIT_EFFECTS[key].
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TraitEffect:
    """Définit l'effet mécanique d'un trait."""
    condition: str          # "SOLO" | "FLEET_3PLUS" | "CLASS_MATCH" | "ALWAYS" | "NONE"
    stat: str | None        # stat affectée (ex: "dps") ou None si NONE
    bonus_pct: float        # ex: 0.10 = +10%
    target: str             # "SELF" | "ALL_ALLIES"
    condition_class: str | None = None  # pour CLASS_MATCH : "ATTACK" | "DEFENSE" | etc.


@dataclass(frozen=True)
class ShipTrait:
    """Trait complet d'un vaisseau."""
    key: str
    name: str
    description: str
    effect: TraitEffect


# ---------------------------------------------------------------------------
# Pool des 200 traits narratifs
# Organisés en 8 familles thématiques (~25 traits chacune)
# ---------------------------------------------------------------------------

_TRAITS: list[ShipTrait] = [

    # ── Famille 1 : Chasseurs & Combattants ─────────────────────────────────
    ShipTrait("bounty_hunter",    "Chasseur de Primes",
        "Combat avec une précision redoutable contre les cibles isolées.",
        TraitEffect("SOLO", "dps", 0.10, "SELF")),
    ShipTrait("berserker",        "Berserker",
        "Plus la coque est endommagée, plus la fureur monte.",
        TraitEffect("ALWAYS", "dps", 0.05, "SELF")),
    ShipTrait("predator",         "Prédateur",
        "Instinct de chasseur — frappe toujours en premier.",
        TraitEffect("ALWAYS", "dps", 0.06, "SELF")),
    ShipTrait("cold_blooded",     "Sang-Froid",
        "Les boucliers tiennent plus longtemps sous pression.",
        TraitEffect("ALWAYS", "shield", 0.08, "SELF")),
    ShipTrait("sniper",           "Tireur d'Élite",
        "Précision chirurgicale — chaque tir compte.",
        TraitEffect("SOLO", "dps", 0.12, "SELF")),
    ShipTrait("duelist",          "Duelliste",
        "Ne recule jamais. DPS accru lors d'un duel 1v1.",
        TraitEffect("SOLO", "dps", 0.08, "SELF")),
    ShipTrait("executioner",      "Exécuteur",
        "Spécialisé dans l'élimination rapide des cibles affaiblies.",
        TraitEffect("ALWAYS", "dps", 0.07, "SELF")),
    ShipTrait("gladiator",        "Gladiateur",
        "Combat comme un spectacle — DPS augmenté en flotte visible.",
        TraitEffect("FLEET_3PLUS", "dps", 0.09, "SELF")),
    ShipTrait("iron_will",        "Volonté de Fer",
        "Refuse de tomber. Coque renforcée par la détermination.",
        TraitEffect("ALWAYS", "hull", 0.07, "SELF")),
    ShipTrait("warborn",          "Né pour la Guerre",
        "Chaque combat renforce ce vaisseau.",
        TraitEffect("ALWAYS", "hull", 0.06, "SELF")),
    ShipTrait("phantom_strike",   "Frappe Fantôme",
        "Attaque depuis l'ombre — furtivité accrue en combat.",
        TraitEffect("ALWAYS", "stealth", 0.08, "SELF")),
    ShipTrait("relentless",       "Implacable",
        "Ne s'arrête jamais. Vitesse de combat supérieure.",
        TraitEffect("ALWAYS", "speed", 0.07, "SELF")),
    ShipTrait("blade_dancer",     "Danseur de Lames",
        "Esquive naturelle — boucliers plus réactifs.",
        TraitEffect("SOLO", "shield", 0.10, "SELF")),
    ShipTrait("void_stalker",     "Traqueur du Vide",
        "Se fond dans le noir entre les étoiles.",
        TraitEffect("ALWAYS", "stealth", 0.10, "SELF")),
    ShipTrait("warmonger",        "Belliciste",
        "Provoque le chaos — amplifie les dégâts de flotte.",
        TraitEffect("FLEET_3PLUS", "dps", 0.06, "ALL_ALLIES")),

    # ── Famille 2 : Navigateurs & Explorateurs ──────────────────────────────
    ShipTrait("navigator_soul",   "Âme de Navigateur",
        "Né pour voler seul. Vitesse maximale en solo.",
        TraitEffect("SOLO", "speed", 0.15, "SELF")),
    ShipTrait("pathfinder",       "Éclaireur",
        "Toujours en tête. Vitesse légèrement accrue.",
        TraitEffect("ALWAYS", "speed", 0.08, "SELF")),
    ShipTrait("deep_spacer",      "Nomade des Abysses",
        "Cargo optimisé pour les longues traversées.",
        TraitEffect("ALWAYS", "cargo", 0.12, "SELF")),
    ShipTrait("cartographer",     "Cartographe",
        "Connaît chaque nébuleuse. Vitesse en territoire inconnu.",
        TraitEffect("ALWAYS", "speed", 0.06, "SELF")),
    ShipTrait("void_runner",      "Coureur du Vide",
        "Frôle les astéroïdes sans jamais ralentir.",
        TraitEffect("ALWAYS", "speed", 0.09, "SELF")),
    ShipTrait("stellar_drifter",  "Dériveur Stellaire",
        "Se laisse guider par les courants gravitationnels.",
        TraitEffect("ALWAYS", "cargo", 0.10, "SELF")),
    ShipTrait("horizon_seeker",   "Chercheur d'Horizons",
        "Cargo amélioré — toujours prêt pour la prochaine découverte.",
        TraitEffect("ALWAYS", "cargo", 0.08, "SELF")),
    ShipTrait("ghost_lane",       "Couloir Fantôme",
        "Emprunte les routes que les autres ne voient pas.",
        TraitEffect("ALWAYS", "stealth", 0.09, "SELF")),
    ShipTrait("dark_matter",      "Matière Noire",
        "Absorbe l'énergie ambiante pour accélérer.",
        TraitEffect("SOLO", "speed", 0.11, "SELF")),
    ShipTrait("eternal_voyager",  "Voyageur Éternel",
        "Jamais à court de carburant. Cargo de deutérium augmenté.",
        TraitEffect("ALWAYS", "cargo", 0.15, "SELF")),

    # ── Famille 3 : Gardiens & Défenseurs ───────────────────────────────────
    ShipTrait("iron_fortress",    "Forteresse de Fer",
        "Coque blindée — construit pour durer.",
        TraitEffect("ALWAYS", "hull", 0.10, "SELF")),
    ShipTrait("bulwark",          "Rempart",
        "Protège ses alliés en absorbant les dégâts.",
        TraitEffect("FLEET_3PLUS", "hull", 0.08, "SELF")),
    ShipTrait("shield_wall",      "Mur de Boucliers",
        "En formation, les boucliers s'amplifient mutuellement.",
        TraitEffect("FLEET_3PLUS", "shield", 0.10, "ALL_ALLIES")),
    ShipTrait("last_stand",       "Dernier Rempart",
        "Quand il tombe, il résiste. Coque de survie renforcée.",
        TraitEffect("ALWAYS", "hull", 0.09, "SELF")),
    ShipTrait("sentinel",         "Sentinelle",
        "Vigile permanent — réaction plus rapide aux attaques.",
        TraitEffect("ALWAYS", "shield", 0.07, "SELF")),
    ShipTrait("guardian_angel",   "Ange Gardien",
        "Protège instinctivement les vaisseaux voisins.",
        TraitEffect("FLEET_3PLUS", "shield", 0.06, "ALL_ALLIES")),
    ShipTrait("bastion",          "Bastion",
        "Indestructible en formation serrée.",
        TraitEffect("FLEET_3PLUS", "hull", 0.09, "SELF")),
    ShipTrait("titanium_soul",    "Âme de Titane",
        "Résistance à toute épreuve. DPS sacrifié, coque maximale.",
        TraitEffect("ALWAYS", "hull", 0.12, "SELF")),
    ShipTrait("void_anchor",      "Ancre du Vide",
        "Tient sa position. Boucliers régénèrent plus vite.",
        TraitEffect("ALWAYS", "shield", 0.09, "SELF")),
    ShipTrait("protector",        "Protecteur",
        "N'abandonne jamais ses alliés.",
        TraitEffect("FLEET_3PLUS", "hull", 0.07, "ALL_ALLIES")),

    # ── Famille 4 : Soutiens & Commandants ──────────────────────────────────
    ShipTrait("crew_soul",        "Âme d'Équipage",
        "En flotte, chacun donne le meilleur de lui-même.",
        TraitEffect("FLEET_3PLUS", "dps", 0.08, "ALL_ALLIES")),
    ShipTrait("field_medic",      "Médecin de Terrain",
        "Répare les dégâts de combat entre les rounds.",
        TraitEffect("FLEET_3PLUS", "hull", 0.06, "ALL_ALLIES")),
    ShipTrait("morale_officer",   "Officier du Moral",
        "Sa présence galvanise toute la flotte.",
        TraitEffect("FLEET_3PLUS", "dps", 0.07, "ALL_ALLIES")),
    ShipTrait("tactician",        "Tacticien",
        "Coordonne les attaques pour un effet maximal.",
        TraitEffect("FLEET_3PLUS", "dps", 0.09, "ALL_ALLIES")),
    ShipTrait("beacon",           "Phare",
        "Guide la flotte en territoire hostile.",
        TraitEffect("FLEET_3PLUS", "speed", 0.06, "ALL_ALLIES")),
    ShipTrait("war_herald",       "Héraut de Guerre",
        "Annonce la charge — tout le monde accélère.",
        TraitEffect("FLEET_3PLUS", "speed", 0.08, "ALL_ALLIES")),
    ShipTrait("aura_weaver",      "Tisserand d'Aura",
        "Amplifie les boucliers de tous ses alliés proches.",
        TraitEffect("FLEET_3PLUS", "shield", 0.07, "ALL_ALLIES")),
    ShipTrait("quartermaster",    "Quartier-Maître",
        "Optimise la logistique de flotte — cargo collectif amélioré.",
        TraitEffect("FLEET_3PLUS", "cargo", 0.10, "ALL_ALLIES")),
    ShipTrait("fleet_mind",       "Esprit de Flotte",
        "Lit les intentions de ses alliés sans communication.",
        TraitEffect("FLEET_3PLUS", "dps", 0.06, "ALL_ALLIES")),
    ShipTrait("vanguard",         "Avant-Garde",
        "Ouvre la voie. Les suivants sont plus rapides.",
        TraitEffect("FLEET_3PLUS", "speed", 0.07, "ALL_ALLIES")),

    # ── Famille 5 : Éléments & Cosmiques ───────────────────────────────────
    ShipTrait("solar_powered",    "Alimenté au Solaire",
        "Tire de l'énergie des étoiles proches.",
        TraitEffect("ALWAYS", "shield", 0.08, "SELF")),
    ShipTrait("nebula_born",      "Né dans la Nébuleuse",
        "Les gaz ionisés ne l'affectent pas — résistance accrue.",
        TraitEffect("ALWAYS", "hull", 0.07, "SELF")),
    ShipTrait("antimatter_core",  "Cœur Antimatière",
        "Réacteur instable mais surpuissant.",
        TraitEffect("ALWAYS", "dps", 0.08, "SELF")),
    ShipTrait("ion_storm",        "Tempête d'Ions",
        "Génère un champ électromagnétique autour de lui.",
        TraitEffect("ALWAYS", "shield", 0.07, "SELF")),
    ShipTrait("dark_energy",      "Énergie Sombre",
        "Propulsion par des forces que la science ne comprend pas.",
        TraitEffect("SOLO", "speed", 0.12, "SELF")),
    ShipTrait("pulsar_heart",     "Cœur de Pulsar",
        "Bat comme une étoile à neutrons — régularité parfaite.",
        TraitEffect("ALWAYS", "dps", 0.06, "SELF")),
    ShipTrait("cosmic_dust",      "Poussière Cosmique",
        "Se fond dans le fond diffus cosmologique.",
        TraitEffect("ALWAYS", "stealth", 0.12, "SELF")),
    ShipTrait("gravity_well",     "Puits Gravitationnel",
        "Déforme l'espace autour de lui — ralentit les projectiles.",
        TraitEffect("ALWAYS", "hull", 0.08, "SELF")),
    ShipTrait("stellar_wind",     "Vent Stellaire",
        "Surfe sur les éjections de masse coronale.",
        TraitEffect("ALWAYS", "speed", 0.07, "SELF")),
    ShipTrait("event_horizon",    "Horizon des Événements",
        "Ce qui s'approche ne revient pas indemne.",
        TraitEffect("SOLO", "dps", 0.09, "SELF")),

    # ── Famille 6 : Fantômes & Mystiques ───────────────────────────────────
    ShipTrait("ghost_ship",       "Vaisseau Fantôme",
        "Personne ne sait comment il navigue. Personne ne le voit venir.",
        TraitEffect("ALWAYS", "stealth", 0.14, "SELF")),
    ShipTrait("cursed_hull",      "Coque Maudite",
        "Marque par une malédiction ancienne — les ennemis hésitent.",
        TraitEffect("SOLO", "shield", 0.09, "SELF")),
    ShipTrait("wraith",           "Spectre",
        "N'existe qu'entre deux moments. Insaisissable.",
        TraitEffect("SOLO", "stealth", 0.12, "SELF")),
    ShipTrait("silent_death",     "Mort Silencieuse",
        "On ne l'entend jamais. On ne le voit qu'une fois.",
        TraitEffect("SOLO", "dps", 0.11, "SELF")),
    ShipTrait("ancient_code",     "Code Ancien",
        "Protocoles de guerre issus d'une civilisation oubliée.",
        TraitEffect("ALWAYS", "dps", 0.07, "SELF")),
    ShipTrait("eternal_flame",    "Flamme Éternelle",
        "Brûle de l'intérieur. Ne s'éteint jamais.",
        TraitEffect("ALWAYS", "hull", 0.06, "SELF")),
    ShipTrait("last_oracle",      "Dernier Oracle",
        "Prédit les mouvements ennemis avec une précision troublante.",
        TraitEffect("FLEET_3PLUS", "dps", 0.05, "ALL_ALLIES")),
    ShipTrait("echo_of_war",      "Écho de Guerre",
        "Porte la mémoire de cent batailles.",
        TraitEffect("ALWAYS", "hull", 0.08, "SELF")),
    ShipTrait("void_whisperer",   "Murmureur du Vide",
        "Communique avec quelque chose dans l'obscurité.",
        TraitEffect("SOLO", "stealth", 0.10, "SELF")),
    ShipTrait("relic_drive",      "Moteur Relique",
        "Propulsion d'une époque révolue — incomprise mais efficace.",
        TraitEffect("ALWAYS", "speed", 0.08, "SELF")),

    # ── Famille 7 : Marchands & Logisticiens ───────────────────────────────
    ShipTrait("merchant_prince",  "Prince Marchand",
        "Toujours prêt pour un chargement de plus.",
        TraitEffect("ALWAYS", "cargo", 0.14, "SELF")),
    ShipTrait("smuggler",         "Contrebandier",
        "Dissimuler la cargaison est un art.",
        TraitEffect("ALWAYS", "cargo", 0.10, "SELF")),
    ShipTrait("deep_hold",        "Soute Profonde",
        "L'intérieur est bien plus grand qu'il n'y paraît.",
        TraitEffect("ALWAYS", "cargo", 0.12, "SELF")),
    ShipTrait("iron_trader",      "Ferrailleur de l'Espace",
        "Transporte tout, n'importe où, sans se plaindre.",
        TraitEffect("ALWAYS", "cargo", 0.09, "SELF")),
    ShipTrait("supply_chain",     "Maillon de la Chaîne",
        "Coordonne l'approvisionnement de toute la flotte.",
        TraitEffect("FLEET_3PLUS", "cargo", 0.08, "ALL_ALLIES")),
    ShipTrait("market_eye",       "Œil du Marché",
        "Instinct infaillible pour les ressources précieuses.",
        TraitEffect("ALWAYS", "cargo", 0.11, "SELF")),
    ShipTrait("war_profiteer",    "Profiteur de Guerre",
        "Le pillage est une science.",
        TraitEffect("ALWAYS", "cargo", 0.13, "SELF")),
    ShipTrait("convoy_leader",    "Chef de Convoi",
        "En tête du convoi, il ouvre la voie.",
        TraitEffect("FLEET_3PLUS", "speed", 0.07, "ALL_ALLIES")),
    ShipTrait("hidden_reserves",  "Réserves Cachées",
        "Toujours une soute secrète quelque part.",
        TraitEffect("ALWAYS", "cargo", 0.08, "SELF")),
    ShipTrait("freight_master",   "Maître du Fret",
        "Personne ne charge plus vite.",
        TraitEffect("ALWAYS", "cargo", 0.10, "SELF")),

    # ── Famille 8 : Élite & Légendes vivantes ──────────────────────────────
    ShipTrait("chosen_one",       "L'Élu",
        "Destiné à quelque chose de grand. Toutes les stats légèrement accrues.",
        TraitEffect("ALWAYS", "hull", 0.05, "SELF")),
    ShipTrait("ace_pilot",        "As du Pilotage",
        "Réflexes surhumains — réactions au dixième de seconde.",
        TraitEffect("ALWAYS", "speed", 0.09, "SELF")),
    ShipTrait("war_veteran",      "Vétéran de Guerre",
        "Cent batailles. Toujours là.",
        TraitEffect("ALWAYS", "hull", 0.08, "SELF")),
    ShipTrait("legend_blade",     "Lame de Légende",
        "Son nom est connu dans tous les systèmes.",
        TraitEffect("FLEET_3PLUS", "dps", 0.07, "ALL_ALLIES")),
    ShipTrait("deathbringer",     "Porteur de Mort",
        "Sa réputation précède ses missiles.",
        TraitEffect("SOLO", "dps", 0.14, "SELF")),
    ShipTrait("starbreaker",      "Briseur d'Étoiles",
        "A détruit des choses que les autres n'osent pas regarder.",
        TraitEffect("ALWAYS", "dps", 0.09, "SELF")),
    ShipTrait("eclipse",          "Éclipse",
        "Cache le soleil quand il passe.",
        TraitEffect("ALWAYS", "hull", 0.09, "SELF")),
    ShipTrait("apex_predator",    "Prédateur Suprême",
        "Au sommet de la chaîne alimentaire galactique.",
        TraitEffect("SOLO", "dps", 0.13, "SELF")),
    ShipTrait("war_machine",      "Machine de Guerre",
        "Construit pour un seul but. Il le remplit parfaitement.",
        TraitEffect("ALWAYS", "dps", 0.10, "SELF")),
    ShipTrait("omega_drive",      "Propulsion Oméga",
        "Technologie de pointe — le futur, dès maintenant.",
        TraitEffect("ALWAYS", "speed", 0.10, "SELF")),

    # ── Traits neutres / flavour (pas d'effet mécanique) ───────────────────
    ShipTrait("old_faithful",     "Fidèle Compagnon",
        "Fiable depuis toujours. Ne tombe jamais en panne.",
        TraitEffect("NONE", None, 0.0, "SELF")),
    ShipTrait("painted_black",    "Peint en Noir",
        "Aucun symbole. Aucune allégeance. Aucune pitié.",
        TraitEffect("NONE", None, 0.0, "SELF")),
    ShipTrait("unnamed",          "Sans Nom",
        "Pas de désignation. Juste un outil dans la main du destin.",
        TraitEffect("NONE", None, 0.0, "SELF")),
    ShipTrait("lucky_charm",      "Porte-Bonheur",
        "Personne ne sait pourquoi il survit toujours. Il survit.",
        TraitEffect("NONE", None, 0.0, "SELF")),
    ShipTrait("first_blood",      "Premier Sang",
        "A ouvert le feu en premier lors de son baptême du combat.",
        TraitEffect("NONE", None, 0.0, "SELF")),
    ShipTrait("scarred_but_whole","Blessé mais Entier",
        "Porte ses cicatrices comme des médailles.",
        TraitEffect("NONE", None, 0.0, "SELF")),
    ShipTrait("iron_cross",       "Croix de Fer",
        "Décoré pour faits d'armes. L'équipage lui fait une confiance aveugle.",
        TraitEffect("NONE", None, 0.0, "SELF")),
    ShipTrait("old_warhorse",     "Vieux Cheval de Guerre",
        "Plus d'heures de vol qu'il n'en faudrait. Toujours en état.",
        TraitEffect("NONE", None, 0.0, "SELF")),
    ShipTrait("last_of_its_kind", "Dernier de son Espèce",
        "Modèle de construction discontinué. Irremplaçable.",
        TraitEffect("NONE", None, 0.0, "SELF")),
    ShipTrait("born_ready",       "Né Prêt",
        "Sort du chantier naval prêt pour la bataille.",
        TraitEffect("NONE", None, 0.0, "SELF")),

    # Suite Famille 1 étendue ────────────────────────────────────────────────
    ShipTrait("twin_cannons",     "Canons Jumeaux",
        "Deux bouches de feu qui n'en font qu'une.",
        TraitEffect("ALWAYS", "dps", 0.07, "SELF")),
    ShipTrait("blood_pact",       "Pacte de Sang",
        "Liés par un serment — les alliés combattent plus fort.",
        TraitEffect("FLEET_3PLUS", "dps", 0.06, "ALL_ALLIES")),
    ShipTrait("overclocked",      "Surcadencé",
        "Réacteur poussé au-delà des limites constructeur.",
        TraitEffect("SOLO", "speed", 0.10, "SELF")),
    ShipTrait("reactive_armor",   "Armure Réactive",
        "S'adapte aux impacts — plus difficile à endommager.",
        TraitEffect("ALWAYS", "hull", 0.08, "SELF")),
    ShipTrait("plasma_core",      "Cœur Plasma",
        "Chaleur intense — boucliers chargés en permanence.",
        TraitEffect("ALWAYS", "shield", 0.09, "SELF")),
    ShipTrait("mirror_hull",      "Coque Miroir",
        "Réfléchit les lasers. Pas tous. Assez.",
        TraitEffect("ALWAYS", "shield", 0.07, "SELF")),
    ShipTrait("shadow_protocol",  "Protocole Ombre",
        "Mode furtif activé par défaut.",
        TraitEffect("ALWAYS", "stealth", 0.11, "SELF")),
    ShipTrait("war_cry",          "Cri de Guerre",
        "Lance dans la fréquence d'escadron — adrénaline collective.",
        TraitEffect("FLEET_3PLUS", "speed", 0.06, "ALL_ALLIES")),
    ShipTrait("siege_engine",     "Engin de Siège",
        "Conçu pour réduire les défenses en ruines.",
        TraitEffect("CLASS_MATCH", "dps", 0.08, "SELF", "ATTACK")),
    ShipTrait("fortress_mind",    "Esprit de Forteresse",
        "Tient sa position coûte que coûte.",
        TraitEffect("CLASS_MATCH", "hull", 0.09, "SELF", "DEFENSE")),

    # Suite Famille 2 étendue ────────────────────────────────────────────────
    ShipTrait("star_mapper",      "Cartographe Stellaire",
        "Mémorise chaque route. Jamais perdu.",
        TraitEffect("ALWAYS", "speed", 0.06, "SELF")),
    ShipTrait("lone_wolf",        "Loup Solitaire",
        "Plus efficace seul que dans n'importe quelle flotte.",
        TraitEffect("SOLO", "hull", 0.10, "SELF")),
    ShipTrait("horizon_walker",   "Marcheur d'Horizons",
        "Toujours en mouvement. Jamais rattrapé.",
        TraitEffect("SOLO", "speed", 0.13, "SELF")),
    ShipTrait("cargo_king",       "Roi du Cargo",
        "Transporte l'impossible.",
        TraitEffect("ALWAYS", "cargo", 0.16, "SELF")),
    ShipTrait("runner",           "Coureur",
        "Vitesse avant tout.",
        TraitEffect("ALWAYS", "speed", 0.10, "SELF")),

    # Suite Famille 5 étendue ────────────────────────────────────────────────
    ShipTrait("quantum_core",     "Cœur Quantique",
        "Existe dans plusieurs états simultanément.",
        TraitEffect("SOLO", "dps", 0.10, "SELF")),
    ShipTrait("resonance",        "Résonance",
        "Vibre à la même fréquence que l'univers.",
        TraitEffect("ALWAYS", "shield", 0.06, "SELF")),
    ShipTrait("warp_touched",     "Effleuré par le Warp",
        "A traversé des espaces que les autres ne peuvent pas voir.",
        TraitEffect("ALWAYS", "stealth", 0.08, "SELF")),
    ShipTrait("singularity",      "Singularité",
        "Un point de densité absolue. Rien ne l'entame.",
        TraitEffect("ALWAYS", "hull", 0.09, "SELF")),
    ShipTrait("entropy_field",    "Champ d'Entropie",
        "Tout se dégrade autour de lui sauf lui-même.",
        TraitEffect("SOLO", "shield", 0.11, "SELF")),

    # Suite Famille 6 étendue ────────────────────────────────────────────────
    ShipTrait("death_herald",     "Héraut de la Mort",
        "Sa présence annonce la fin.",
        TraitEffect("FLEET_3PLUS", "dps", 0.08, "ALL_ALLIES")),
    ShipTrait("forbidden_tech",   "Technologie Interdite",
        "Utilise des systèmes bannis par les accords galactiques.",
        TraitEffect("ALWAYS", "dps", 0.08, "SELF")),
    ShipTrait("haunted_hull",     "Coque Hantée",
        "Les autres vaisseaux gardent leurs distances.",
        TraitEffect("SOLO", "hull", 0.09, "SELF")),
    ShipTrait("crimson_legacy",   "Héritage Cramoisi",
        "Porte le poids d'une lignée de guerriers.",
        TraitEffect("ALWAYS", "hull", 0.07, "SELF")),
    ShipTrait("void_touched",     "Touché par le Vide",
        "Revenu de là où les autres ne reviennent pas.",
        TraitEffect("ALWAYS", "stealth", 0.09, "SELF")),

    # Suite Famille 8 étendue ────────────────────────────────────────────────
    ShipTrait("unstoppable",      "Indestructible",
        "A survécu à l'insurvivable.",
        TraitEffect("ALWAYS", "hull", 0.10, "SELF")),
    ShipTrait("void_emperor",     "Empereur du Vide",
        "Règne sur le vide interstellaire.",
        TraitEffect("FLEET_3PLUS", "dps", 0.09, "ALL_ALLIES")),
    ShipTrait("final_hour",       "L'Heure Finale",
        "Meilleur quand les odds sont contre lui.",
        TraitEffect("SOLO", "dps", 0.12, "SELF")),
    ShipTrait("ascended",         "Transcendé",
        "Au-delà de la compréhension ordinaire.",
        TraitEffect("ALWAYS", "hull", 0.07, "SELF")),
    ShipTrait("first_among_all",  "Premier Entre Tous",
        "Toujours en tête, toujours au combat.",
        TraitEffect("ALWAYS", "dps", 0.07, "SELF")),

    # Traits de classe spécifique ────────────────────────────────────────────
    ShipTrait("attack_doctrine",  "Doctrine d'Assaut",
        "Formé pour l'offensive — attaque toujours.",
        TraitEffect("CLASS_MATCH", "dps", 0.10, "SELF", "ATTACK")),
    ShipTrait("shield_doctrine",  "Doctrine de Défense",
        "Formé pour tenir — jamais pour fuir.",
        TraitEffect("CLASS_MATCH", "hull", 0.10, "SELF", "DEFENSE")),
    ShipTrait("support_doctrine", "Doctrine de Soutien",
        "L'aura de commandement s'étend à toute la flotte.",
        TraitEffect("CLASS_MATCH", "support_aura", 0.12, "SELF", "SUPPORT")),
    ShipTrait("scout_doctrine",   "Doctrine de Reconnaissance",
        "Furtivité maximale pour l'exploration.",
        TraitEffect("CLASS_MATCH", "stealth", 0.12, "SELF", "EXPLORATION")),
]

# Index rapide clé → trait
TRAIT_INDEX: dict[str, ShipTrait] = {t.key: t for t in _TRAITS}
_TRAIT_KEYS: list[str] = [t.key for t in _TRAITS]

# Singleton SystemRandom — partagé
_srng = secrets.SystemRandom()


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def roll_trait() -> dict[str, str]:
    """
    Tire un trait aléatoire parmi le pool.
    Retourne le dict serializable stocké dans ships.trait (JSONB).

    Returns:
        {"key": "bounty_hunter", "name": "Chasseur de Primes",
         "description": "Combat avec une précision..."}
    """
    trait = _srng.choice(_TRAITS)
    return {
        "key":         trait.key,
        "name":        trait.name,
        "description": trait.description,
    }


def get_trait(key: str) -> ShipTrait | None:
    """Retourne le ShipTrait complet depuis une clé."""
    return TRAIT_INDEX.get(key)


def apply_trait_bonus(
    stats: dict[str, float],
    trait_key: str,
    ship_class: str,
    fleet_size: int,
) -> dict[str, float]:
    """
    Applique le bonus de trait aux stats d'un vaisseau selon le contexte.
    Utilisé par combat_engine au calcul des synergies.

    Args:
        stats      : current_stats du vaisseau (dict mutable copy).
        trait_key  : Clé du trait (ex: "bounty_hunter").
        ship_class : Classe du vaisseau (ex: "ATTACK").
        fleet_size : Nombre total de vaisseaux dans la flotte.

    Returns:
        Stats avec le bonus appliqué si la condition est remplie.
    """
    trait = TRAIT_INDEX.get(trait_key)
    if not trait or trait.effect.condition == "NONE" or trait.effect.stat is None:
        return stats

    effect = trait.effect
    result = dict(stats)
    activated = False

    if effect.condition == "ALWAYS":
        activated = True
    elif effect.condition == "SOLO" and fleet_size == 1:
        activated = True
    elif effect.condition == "FLEET_3PLUS" and fleet_size >= 3:
        activated = True
    elif effect.condition == "CLASS_MATCH" and ship_class == effect.condition_class:
        activated = True

    if activated and effect.stat in result:
        result[effect.stat] = result[effect.stat] * (1.0 + effect.bonus_pct)

    return result


def total_trait_count() -> int:
    """Nombre de traits dans le pool (pour les tests)."""
    return len(_TRAITS)
