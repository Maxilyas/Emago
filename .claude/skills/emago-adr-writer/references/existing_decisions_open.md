# Décisions ouvertes Emago — candidates pour ADR

Extraites de `docs/01_chef_de_projet.md` section 8 et `docs/10_ameliorations.md` section 5.

## Décisions ouvertes prioritaires

| # | Question | Urgence | Agents | Notes |
|---:|---|---|---|---|
| 1 | Limite MAX vaisseaux par hangar | Moyenne | 2 + 7 | 50 / 100 / illimité avec coût ? Impact UI Hangar + perf SELECT ships |
| 2 | Saisons / univers permanent / reset | Basse | 1 + 2 | Permanent vs Saisons 3 mois ? Impact rétention vs équité long terme |
| 3 | Stratégie monétisation cosmétiques | Basse | 1 | Boutique skins / sans monétisation ? Engagement financement projet |
| 4 | Tutoriel/onboarding premier joueur | Haute | 4 + 6 | Story-driven vs quickstart vs les deux ? Critique rétention nouveaux |
| 5 | Système d'espionnage | Moyenne | 2 + 5 | Plusieurs designs possibles, GDD à finaliser puis ADR sur archi |
| 6 | Anti-farm protection débutants | Haute | 2 + 8 | Protection X jours / score-based ? Impact sur newbies vs équité |
| 7 | Mécaniques alliance avancées | Basse | 2 + 3 | Diplomatie, sous-guildes, chat ? Pas urgent Phase 2 |
| 8 | Purge `combat_logs` anciens | Basse | 7 + 9 | Archive S3 vs DELETE >30j ? Décision opérationnelle |
| 9 | Celery vs APScheduler à >1000 joueurs | Basse | 3 + 9 | À benchmark. Voir ADR-003 actuel |
| 10 | WebSocket horizontal sticky sessions | Basse | 3 + 9 | Nginx ip_hash vs Redis pub/sub strict ? Voir ADR-004 |
| 11 | Stockage skins cosmétiques | Basse | 3 + 7 | URL fichiers statiques vs JSONB ? À reporter Phase 3 |
| 12 | CSP plus stricte | Moyenne | 8 + 9 | Suppression `unsafe-inline` ? Impact sur libs frontend |
| 13 | Migration `_active_research` mémoire → BDD | Haute | 5 + 7 | Bug critique : perdu au redémarrage Uvicorn. Décision triviale → pas besoin d'ADR si juste impl |
| 14 | Multi-VPS api+db séparés | Basse | 3 + 9 | À 500+ joueurs |
| 15 | pgBouncer | Basse | 7 + 9 | Idem |

## Critères pour transformer en ADR

Une question ouverte mérite un ADR si :

- ☐ Elle implique ≥ 2 options techniquement viables (pas une simple "à faire").
- ☐ Elle a un impact sur ≥ 2 agents.
- ☐ Elle touche la stack ou la perf prod ou la sécurité.
- ☐ Elle est difficilement réversible après implémentation.
- ☐ Elle suscite débat dans l'équipe.

## Anti-patterns

Une question NE devrait PAS faire l'objet d'un ADR si :

- C'est une simple tâche d'implémentation déjà décidée (ex. "ajouter un endpoint").
- C'est trivial (renommer une variable, ajouter un index évident).
- L'option est imposée par une contrainte externe (réglementaire, partenaire) — la documenter en commentaire suffit.
- C'est une décision de design jeu pure → utiliser `emago-gdd-writer`.

## Roadmap suggérée des ADRs Phase 2

| Phase | ADR à écrire | Pourquoi |
|---|---|---|
| **2A** (sécurité & robustesse) | ADR sur stratégie tests intégration alliances/combat | Fondation pour Phase 2B |
| **2A** | ADR sur heartbeat WebSocket serveur-side | Robustesse connexions |
| **2B** (mécaniques) | ADR sur architecture espionnage (sondes, contre-espionnage) | Décisions structurantes BDD + WS |
| **2B** | ADR sur module inventory (table dédiée vs JSONB sur player) | Impact perf + UX hangar |
| **2C** (perf & scale) | ADR sur partitionnement `combat_logs` | À 1M lignes |
| **2C** | ADR sur scale-out multi-VPS | À 500+ joueurs |
| **3** | ADR sur Celery (revoir ADR-003) | Si scheduler dépasse 1k joueurs |
| **3** | ADR sur saisons vs permanent | Choix structurant retention |
