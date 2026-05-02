# Router → tests requis (gaps actuels)

Source : `docs/08_qa_securite.md` section 5. Liste des tests à compléter par router pour atteindre une couverture sécurité satisfaisante.

## auth (déjà couvert)

✅ `tests/routers/test_auth.py` couvre register/login/refresh avec 12 tests. **Statut : OK.**

## ships (couvert)

✅ `tests/routers/test_ships.py` 11 tests dont 2 vecteurs sécurité. **Statut : OK.**

## forge (couvert basique)

⚠️ `tests/routers/test_forge.py` 5 tests. **À compléter** :
- `test_forge_double_submission` (V2)
- `test_forge_pedigree_other_player_parent` (V9)
- `test_forge_legendary_rejected` (V12)
- `test_forge_history_pagination`
- `test_forge_drift_5pct_distribution` (statistique sur 100 forges)

## planets (à écrire)

❌ Aucun fichier `test_planets.py`. **À écrire** :
- `test_build_already_in_queue` (409)
- `test_build_unknown_building` (400)
- `test_build_insufficient_resources_with_floor` (402, V12 math.floor)
- `test_queue_listing`
- `test_planet_homeworld_auto_creation` (sur un nouveau player)
- `test_planet_other_player_returns_404` (V1)

## fleets (à écrire)

❌ Aucun fichier `test_fleets.py`. **À écrire** :
- `test_send_fleet_success`
- `test_send_with_other_player_ship` (V1, 403 explicite ici)
- `test_send_with_in_flight_ship` (409)
- `test_send_with_insufficient_cargo_capacity` (422)
- `test_recall_already_arrived` (409)
- `test_recall_already_recalled` (409)
- `test_incoming_only_enemies` (filter logic)
- `test_incoming_no_origin_exposed` (response shape n'expose pas origin_planet_id ni owner_id)

## combat (à écrire)

❌ Aucun fichier `test_combat.py`. **À écrire** :
- `test_get_combat_not_participant` (403, V8)
- `test_get_combat_unknown` (404)
- `test_history_limit_capped`
- `test_get_combat_cache_hit` (Redis lu d'abord, BDD fallback)
- `test_combat_replay_determinism` (même seed → mêmes rounds)

## ranking (à écrire — basique)

❌ Aucun fichier. **À écrire** :
- `test_ranking_top_100`
- `test_ranking_me_with_score`
- `test_ranking_alliance_tag_loaded` (TODO ligne 53 ranking.py — vérifier que c'est ok)

## scars (à écrire)

❌ **À écrire** :
- `test_scars_visible_to_all` (lecture publique sans ownership)
- `test_missions_grade_below_2_returns_403`
- `test_missions_grade_2_plus_returns_list`
- `test_claim_mission_already_completed_already_claimed` (409)
- `test_claim_mission_not_completed_yet` (409)

## galaxy (à écrire — basique)

❌ **À écrire** :
- `test_galaxy_returns_15_slots`
- `test_galaxy_invalid_galaxy_or_system` (400/422)
- `test_galaxy_other_planets_visible` (lecture publique)

## expeditions (à écrire)

❌ **À écrire** :
- `test_launch_max_5_ships` (400 si > 5)
- `test_launch_no_homeworld_returns_404`
- `test_launch_insufficient_deuterium_with_floor` (402, V12)
- `test_launch_with_in_fleet_ship` (409)
- `test_active_redis_persistence` (kill API mid-expedition, restart, vérifier expé toujours là)
- `test_history_filter_completed_only`
- `test_resolution_resources_capped_at_capacity`
- `test_resolution_xp_to_lead_ship`

## tech (à écrire)

❌ **À écrire** :
- `test_research_already_in_progress` (409)
- `test_research_prereq_not_met` (409)
- `test_research_max_level_reached` (409)
- `test_research_completion_applies_bonus`
- `test_active_research_persistence_after_restart` (TODO `_active_research` mémoire — à migrer en BDD)

## daily (à écrire)

❌ **À écrire** :
- `test_login_first_time_streak_1`
- `test_login_consecutive_streak_increments`
- `test_login_skipped_day_streak_reset_to_1`
- `test_login_idempotent_same_day` (déjà claim → already_claimed=True, 200)
- `test_claim_mission_completed_success`
- `test_claim_mission_already_claimed` (409)
- `test_claim_mission_not_completed` (402)
- `test_missions_deterministic_per_player_per_day` (sha256 stable)

## alliances (à écrire)

❌ **À écrire (gros morceau, ~14 tests)** :
- `test_create_already_member` (409)
- `test_create_score_below_500` (403)
- `test_create_dup_name` (409)
- `test_create_dup_tag` (409)
- `test_create_no_homeworld` (404)
- `test_create_insufficient_resources` (402)
- `test_join_full_alliance` (409, ≥20 membres — fixture `alliance_full_20_members`)
- `test_join_already_member` (409)
- `test_leave_self_success`
- `test_leader_cannot_leave_with_others` (409)
- `test_kick_by_officer` (403 si pas officer/leader)
- `test_declare_war_not_leader` (403)
- `test_declare_war_self` (400)
- `test_declare_war_already_active` (409)
- `test_declare_peace_too_early` (409, < 48h)
- `test_war_xp_bonus_applied` (intégration combat — bonus × 1.5 dans XP gagnée)

## modules (couvert basique)

⚠️ Couvert dans `test_ships.py`. **À étendre** :
- `test_install_replace_existing_module`
- `test_install_returns_cap_reached_when_capped`
- `test_install_grade5_ship_with_premium_slot_level5`

## websocket (à écrire — nouveau dossier)

❌ Aucun test WS. **À écrire `tests/websocket/test_handler.py`** :
- `test_connect_invalid_token_closes_4001`
- `test_connect_unknown_player_closes_4004`
- `test_ping_pong`
- `test_forge_poll_returns_status`
- `test_unknown_message_type_returns_error`
- `test_invalid_json_returns_error_continues_loop`
- `test_isolation_player_a_does_not_receive_player_b_events` (V8)
- `test_disconnect_cleanup`
- `test_reconnect_after_disconnect`

## Priorité ordonnée par criticité

1. **Alliances + WebSocket isolation** — Sprint 4 fragile, à blinder.
2. **Combat** — moteur central, replay determinism critique.
3. **Forge double-submission** — V2 critique.
4. **Expeditions Redis persistence** — fix v2 important.
5. **Daily streak edge cases** — perte d'utilisateur si bug.
6. **Tech `_active_research`** — bug connu, doit être test régression après migration BDD.
7. **Planets & fleets** — endpoints fréquents, pas testés.
8. **Galaxy & ranking** — moins critique mais facile à écrire.
