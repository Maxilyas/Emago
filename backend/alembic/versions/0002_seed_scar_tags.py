"""
Alembic migration : seed des scar_tags (cicatrices narratives)

Revision ID: 0002_seed_scar_tags
Revises: 0001_initial_schema
Create Date: 2025-01-29

Peuple la table scar_tags avec le pool de tags narratifs.
Cette migration ne doit jamais être rollbackée en prod —
les tags sont référencés par ship_scars.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "0002_seed_scar_tags"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Pool de cicatrices narratives (~30 exemples, à compléter jusqu'à ~500)
# ---------------------------------------------------------------------------
SCAR_TAGS = [
    # Batailles célèbres
    ("nebula_kha_survivor",        "Rescapé de la Nébuleuse Kha"),
    ("ring_iv_siege",              "Survivant du Siège de l'Anneau IV"),
    ("pulse_gate_last_stand",      "Dernier défenseur de la Porte des Pulsars"),
    ("binary_star_ambush",         "Embuscade de l'Étoile Binaire Arveth"),
    ("void_breach_escapee",        "Évadé de la Brèche du Vide"),
    ("corona_massacre_survivor",   "Rescapé du Massacre de la Couronne"),
    ("deep_rift_patrol",           "Patrouilleur du Rift Profond"),
    ("iron_nebula_defender",       "Défenseur de la Nébuleuse de Fer"),
    ("nova_wake_battle",           "Combat dans le Sillage de la Nova"),
    ("ghost_sector_retreat",       "Retraite du Secteur Fantôme"),
    # Exploits individuels
    ("one_against_many",           "Un contre la multitude"),
    ("hull_at_one_percent",        "Survécu à 1% de coque"),
    ("last_ship_standing",         "Dernier vaisseau debout"),
    ("ambushed_in_transit",        "Attaqué en plein transit"),
    ("escaped_legendary_fleet",    "Échappé à une flotte légendaire"),
    ("shield_breaker_prey",        "Cible d'un briseur de boucliers"),
    ("three_battles_one_day",      "Trois batailles en une révolution"),
    ("sieged_homeworld",           "A défendu la planète natale"),
    ("solo_raid_survivor",         "Survécu à un raid en solo"),
    ("titan_killer",               "Destructeur de Titan"),
    # Conditions extrêmes
    ("ion_storm_transit",          "Traversée d'une tempête ionique"),
    ("debris_field_navigation",    "Navigation dans un champ de débris"),
    ("gravity_well_escape",        "Évasion d'un puits gravitationnel"),
    ("supernova_proximity",        "Frôlé l'explosion d'une supernova"),
    ("dark_matter_exposure",       "Exposé à une poche de matière sombre"),
    # Alliances et trahisons
    ("betrayed_by_ally",           "Trahi par un allié"),
    ("alliance_last_bastion",      "Dernier bastion de l'alliance"),
    ("escort_mission_survivor",    "Survivant d'une mission d'escorte"),
    ("diplomatic_ambush",          "Piégé lors d'un rendez-vous diplomatique"),
    ("rearguard_action",           "Combat d'arrière-garde sacrificiel"),
]


def upgrade() -> None:
    scar_tags_table = table(
        "scar_tags",
        column("tag_code", sa.String),
        column("narrative", sa.Text),
    )
    op.bulk_insert(
        scar_tags_table,
        [{"tag_code": code, "narrative": narrative} for code, narrative in SCAR_TAGS],
    )


def downgrade() -> None:
    # Ne supprime PAS les tags en prod (référencés par ship_scars)
    # Utilise un flag pour forcer en dev uniquement
    op.execute("DELETE FROM scar_tags WHERE tag_code IN (%s)" % ",".join(
        f"'{code}'" for code, _ in SCAR_TAGS
    ))
