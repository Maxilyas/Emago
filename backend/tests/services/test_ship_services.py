"""
tests/services/test_ship_services.py
Tests unitaires — logique pure sans BDD ni Redis.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.services.ship_build_service import (
    _RARITY_MULT,
    _RARITY_THRESHOLDS,
    apply_pedigree_bonus,
    find_best_stat,
    generate_base_stats,
    roll_rarity,
    SHIP_TYPE_BUILD_COST,
    SHIP_TYPE_CLASS,
)
from app.services.ship_stats_service import (
    _GRADE_BONUS,
    _MODULE_BOOST,
    _STAT_CAP_RATIO,
    _compute_current_stats,
    validate_module_slot,
)
from app.services.combat_engine import (
    CombatShip,
    _compute_differential_xp,
    _compute_grade,
    _fleet_power,
    _should_earn_scar,
)
from app.services.forge_service import (
    _RARITY_UPGRADE,
    _XP_TRANSFER_RATIO,
    _merge_best_stats,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_ship_mock(
    ship_class: str = "ATTACK",
    rarity: str = "COMMON",
    grade: int = 0,
    total_slots: int = 2,
    premium_slots: int = 0,
    base_stats: dict | None = None,
) -> MagicMock:
    ship = MagicMock()
    ship.class_ = MagicMock()
    ship.class_.value = ship_class
    ship.ship_class = ship_class   # utilisé par _compute_current_stats
    ship.rarity = MagicMock()
    ship.rarity.value = rarity
    ship.grade = grade
    ship.total_slots = total_slots
    ship.premium_slots = premium_slots
    ship.base_stats = base_stats or {
        "hull": 100, "shield": 20, "dps": 80, "speed": 45.0,
        "cargo": 200, "stealth": 0.0, "support_aura": 0.0,
    }
    return ship


def _make_module_mock(slot_index: int, module_type: str, level: int) -> MagicMock:
    mod = MagicMock()
    mod.slot_index = slot_index
    mod.module_type = module_type
    mod.level = level
    return mod


def _make_combat_ship(
    hull: int = 200, shield: int = 50, dps: int = 60,
    grade: int = 0, ship_class: str = "ATTACK", rarity: str = "COMMON",
) -> CombatShip:
    return CombatShip(
        ship_id=uuid.uuid4(), owner_id=uuid.uuid4(),
        ship_class=ship_class, rarity=rarity, grade=grade,
        base_hull=hull, hull=hull, hull_max=hull,
        shield=shield, shield_max=shield,
        dps=dps, shield_regen=0.0, support_aura=0.0,
    )


# ===========================================================================
# ship_build_service
# ===========================================================================

class TestRollRarity:
    def test_always_valid(self):
        valid = {"COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"}
        for _ in range(300):
            assert roll_rarity() in valid

    def test_common_most_frequent(self):
        counts: dict[str, int] = {}
        for _ in range(2000):
            r = roll_rarity()
            counts[r] = counts.get(r, 0) + 1
        ratio = counts.get("COMMON", 0) / 2000
        assert 0.45 < ratio < 0.65

    def test_thresholds_reach_one(self):
        assert abs(_RARITY_THRESHOLDS[-1][1] - 1.0) < 1e-9

    def test_multiplier_ordering(self):
        order = ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]
        for i in range(len(order) - 1):
            assert _RARITY_MULT[order[i]] < _RARITY_MULT[order[i + 1]]


class TestGenerateBaseStats:
    def test_common_attack_hull_in_range(self):
        for _ in range(100):
            stats = generate_base_stats("ATTACK", "COMMON")
            assert 85 <= stats["hull"] <= 115

    def test_legendary_above_common(self):
        common_hulls = [generate_base_stats("ATTACK", "COMMON")["hull"] for _ in range(50)]
        leg_hulls = [generate_base_stats("ATTACK", "LEGENDARY")["hull"] for _ in range(50)]
        assert min(leg_hulls) > max(common_hulls)

    def test_no_negative_stats(self):
        for cls in ["ATTACK", "DEFENSE", "SUPPORT", "EXPLORATION"]:
            for rar in ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]:
                stats = generate_base_stats(cls, rar)
                for k, v in stats.items():
                    assert v >= 0, f"{cls}/{rar}/{k}={v}"

    def test_speed_one_decimal(self):
        for _ in range(20):
            stats = generate_base_stats("EXPLORATION", "RARE")
            s = str(stats["speed"])
            decimals = len(s.split(".")[-1]) if "." in s else 0
            assert decimals <= 1

    def test_hull_is_int(self):
        for _ in range(20):
            stats = generate_base_stats("DEFENSE", "EPIC")
            assert isinstance(stats["hull"], int)

    def test_unknown_class_raises(self):
        with pytest.raises(ValueError, match="inconnue"):
            generate_base_stats("TITAN", "COMMON")

    def test_unknown_rarity_raises(self):
        with pytest.raises(ValueError, match="inconnue"):
            generate_base_stats("ATTACK", "GODLIKE")


class TestPedigreeBonus:
    def test_boosts_correct_stat(self):
        stats = {"hull": 100, "shield": 20, "dps": 80, "speed": 45.0, "cargo": 200}
        boosted = apply_pedigree_bonus(stats, "hull")
        assert boosted["hull"] == 105
        assert boosted["dps"] == 80

    def test_speed_rounded_to_one_decimal(self):
        stats = {"hull": 100, "shield": 20, "dps": 80, "speed": 90.0, "cargo": 200}
        boosted = apply_pedigree_bonus(stats, "speed")
        assert boosted["speed"] == 94.5

    def test_does_not_mutate_original(self):
        stats = {"hull": 200, "dps": 50}
        apply_pedigree_bonus(stats, "hull")
        assert stats["hull"] == 200

    def test_unknown_stat_noop(self):
        stats = {"hull": 100}
        assert apply_pedigree_bonus(stats, "nonexistent") == {"hull": 100}


class TestFindBestStat:
    def test_returns_highest(self):
        stats = {"hull": 100, "shield": 20, "dps": 80, "speed": 45.0, "cargo": 200}
        assert find_best_stat(stats) == "cargo"

    def test_excludes_stealth_and_aura(self):
        stats = {"hull": 10, "shield": 5, "dps": 8, "speed": 3.0,
                 "cargo": 15, "stealth": 999.0, "support_aura": 888.0}
        assert find_best_stat(stats) == "cargo"


# ===========================================================================
# ship_stats_service
# ===========================================================================

class TestComputeCurrentStats:
    def test_no_modules_grade0_returns_base(self):
        ship = _make_ship_mock(grade=0)
        result = _compute_current_stats(ship, [])
        assert result["hull"] == 100
        assert result["cap_reached"] == []

    def test_grade1_applies_5pct(self):
        ship = _make_ship_mock(grade=1)
        result = _compute_current_stats(ship, [])
        assert result["hull"] == 105
        assert result["dps"] == 84

    def test_grade3_regen_active(self):
        ship = _make_ship_mock(grade=3)
        result = _compute_current_stats(ship, [])
        assert result["shield_regen_per_round"] == 0.02

    def test_cannon_boosts_dps(self):
        ship = _make_ship_mock(ship_class="ATTACK", grade=0)
        mod = _make_module_mock(0, "CANNON", 1)
        result = _compute_current_stats(ship, [mod])
        assert result["dps"] > 80

    def test_affinity_gives_more_than_no_affinity(self):
        ship_att = _make_ship_mock(ship_class="ATTACK")
        ship_def = _make_ship_mock(ship_class="DEFENSE")
        mod = _make_module_mock(0, "CANNON", 1)
        assert _compute_current_stats(ship_att, [mod])["dps"] > _compute_current_stats(ship_def, [mod])["dps"]

    def test_cap_150pct_enforced(self):
        ship = _make_ship_mock(ship_class="ATTACK", total_slots=6, premium_slots=3)
        modules = [_make_module_mock(i, "CANNON", 5) for i in range(6)]
        result = _compute_current_stats(ship, modules)
        assert result["dps"] <= int(80 * (1 + _STAT_CAP_RATIO))
        assert "dps" in result["cap_reached"]

    def test_grade5_stealth_bonus(self):
        ship = _make_ship_mock(ship_class="EXPLORATION", grade=5,
                               base_stats={"hull": 80, "shield": 15, "dps": 12,
                                           "speed": 90.0, "cargo": 3000, "stealth": 25.0, "support_aura": 0.0})
        result = _compute_current_stats(ship, [])
        assert result["stealth"] > 25.0


class TestValidateModuleSlot:
    def test_valid_standard_slot(self):
        ship = _make_ship_mock(total_slots=4, premium_slots=1)
        ok, _ = validate_module_slot(ship, 0, 3)
        assert ok

    def test_slot_out_of_range(self):
        ship = _make_ship_mock(total_slots=2)
        ok, msg = validate_module_slot(ship, 5, 1)
        assert not ok
        assert "invalide" in msg

    def test_level4_needs_premium(self):
        ship = _make_ship_mock(total_slots=4, premium_slots=1)
        ok, msg = validate_module_slot(ship, 0, 4)
        assert not ok
        assert "premium" in msg.lower()

    def test_level4_in_premium_slot_ok(self):
        ship = _make_ship_mock(total_slots=4, premium_slots=1)
        ok, _ = validate_module_slot(ship, 3, 4)
        assert ok


# ===========================================================================
# combat_engine
# ===========================================================================

class TestCombatShipTakeDamage:
    def test_shield_absorbs_first(self):
        cs = _make_combat_ship(hull=200, shield=50)
        result = cs.take_damage(30)
        assert result["shield_absorbed"] == 30
        assert result["hull_damage"] == 0
        assert cs.alive

    def test_overflow_hits_hull(self):
        cs = _make_combat_ship(hull=200, shield=50)
        cs.take_damage(80)
        assert cs.hull == 170
        assert cs.alive

    def test_ship_destroyed(self):
        cs = _make_combat_ship(hull=50, shield=0)
        result = cs.take_damage(100)
        assert not cs.alive
        assert result["destroyed"]

    def test_hull_never_negative(self):
        cs = _make_combat_ship(hull=50, shield=0)
        cs.take_damage(999999)
        assert cs.hull >= 0

    def test_grade4_immunity_first_death(self):
        cs = _make_combat_ship(hull=50, shield=0, grade=4)
        result = cs.take_damage(9999)
        assert cs.hull == 1
        assert cs.alive
        assert cs.immunity_used

    def test_grade4_immunity_only_once(self):
        cs = _make_combat_ship(hull=50, shield=0, grade=4)
        cs.take_damage(9999)  # survit
        cs.take_damage(9999)  # mort
        assert not cs.alive


class TestDifferentialXP:
    def test_equal_power_gives_base(self):
        xp, audit = _compute_differential_xp(100, 1000.0, 1000.0)
        assert xp == 100
        assert audit["diff_factor"] == 0.0

    def test_stronger_enemy_gives_more(self):
        xp, _ = _compute_differential_xp(100, 1000.0, 3000.0)
        assert xp == 600   # 100 × (1 + (3-1)×2.5) = 600

    def test_weaker_enemy_gives_base_minimum(self):
        xp, _ = _compute_differential_xp(100, 5000.0, 100.0)
        assert xp == 100

    def test_audit_keys_present(self):
        _, audit = _compute_differential_xp(80, 1000.0, 2000.0)
        assert {"base_xp", "own_power", "enemy_power", "ratio", "diff_factor", "xp_final"}.issubset(audit)


class TestComputeGrade:
    def test_grade0_below_500(self):
        assert _compute_grade(0) == 0
        assert _compute_grade(499) == 0

    def test_grade1_at_500(self):
        assert _compute_grade(500) == 1

    def test_grade2_at_2000(self):
        assert _compute_grade(2000) == 2

    def test_grade3_at_6000(self):
        assert _compute_grade(6000) == 3

    def test_grade4_at_15000(self):
        assert _compute_grade(15000) == 4

    def test_grade5_at_40000(self):
        assert _compute_grade(40000) == 5
        assert _compute_grade(999999) == 5


class TestFleetPower:
    def test_empty_fleet_returns_one(self):
        assert _fleet_power([]) == 1.0

    def test_stronger_fleet_has_more_power(self):
        weak   = [_make_combat_ship(hull=100, shield=10, dps=10)]
        strong = [_make_combat_ship(hull=500, shield=200, dps=100)]
        assert _fleet_power(strong) > _fleet_power(weak)


class TestShouldEarnScar:
    def test_dead_ship_never_gets_scar(self):
        cs = _make_combat_ship()
        cs.alive = False
        assert not _should_earn_scar(cs, 1000, 100)

    def test_75pct_hull_loss_triggers(self):
        cs = _make_combat_ship(hull=200)
        cs.hull_start = 200
        cs.hull = 49
        assert _should_earn_scar(cs, 100, 100)

    def test_2x_power_ratio_triggers(self):
        cs = _make_combat_ship(hull=200)
        cs.hull_start = 200
        cs.hull = 200
        assert _should_earn_scar(cs, 3000, 1000)

    def test_1_5x_ratio_no_scar(self):
        cs = _make_combat_ship(hull=200)
        cs.hull_start = 200
        cs.hull = 200
        assert not _should_earn_scar(cs, 1500, 1000)


# ===========================================================================
# forge_service
# ===========================================================================

class TestMergeBestStats:
    def test_takes_max_of_each(self):
        a = {"hull": 200, "dps": 50, "shield": 30}
        b = {"hull": 150, "dps": 80, "shield": 25}
        result = _merge_best_stats(a, b)
        assert result == {"hull": 200, "dps": 80, "shield": 30}

    def test_missing_key_handled(self):
        a = {"hull": 200, "stealth": 15.0}
        b = {"hull": 180}
        result = _merge_best_stats(a, b)
        assert result["hull"] == 200
        assert result["stealth"] == 15.0


class TestRarityUpgrade:
    def test_full_chain(self):
        assert _RARITY_UPGRADE["COMMON"]   == "UNCOMMON"
        assert _RARITY_UPGRADE["UNCOMMON"] == "RARE"
        assert _RARITY_UPGRADE["RARE"]     == "EPIC"
        assert _RARITY_UPGRADE["EPIC"]     == "LEGENDARY"

    def test_legendary_not_upgradeable(self):
        assert "LEGENDARY" not in _RARITY_UPGRADE


class TestXPTransfer:
    def test_30pct(self):
        assert int(10_000 * _XP_TRANSFER_RATIO) == 3_000

    def test_ratio_exact(self):
        assert abs(_XP_TRANSFER_RATIO - 0.30) < 1e-9
