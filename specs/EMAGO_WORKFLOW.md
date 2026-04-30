# Emago — Guide de workflow complet
> Version 1.0 — À uploader dans tous les projets Claude.ai

---

## 1. Philosophie du workflow

**Une règle absolue : on ne code jamais avant d'avoir spécifié.**

Chaque rôle est un expert avec un périmètre strict. Il reçoit un contexte, produit un livrable, passe la main. Tu es le chef d'orchestre — tu lis les handoffs, tu décides quand passer au suivant, tu uploades les fichiers dans les bons projets.

---

## 2. Les 4 projets Claude.ai et leur contenu

| Projet | Rôle principal | Fichiers à y uploader |
|---|---|---|
| `Emago — Chef de projet` | Coordination, arbitrage | `EMAGO_WORKFLOW.md`, `emago_agents_prompts.md` |
| `Emago — Conception` | Game Design, Architecture, UI/UX | `gdd.md`, `architecture.md` |
| `Emago — Développement` | Backend, Frontend, BDD | `gdd.md`, `architecture.md`, `schema_bdd.md`, `HANDOFF_agent7_to_agent5.md` |
| `Emago — Qualité & Infra` | QA, DevOps | `gdd.md`, `architecture.md`, `schema_bdd.md` |

> **Règle :** un fichier produit dans un projet est uploadé dans tous les projets qui en ont besoin. Pas de copier-coller de contenu — seulement des uploads de fichiers.

---

## 3. L'ordre des phases (non négociable)

```
Phase 1 — GDD complet          → Rôle : Game Designer (Conception)
Phase 2 — Architecture          → Rôle : Architecte (Conception)
Phase 3 — Schéma BDD            → Rôle : Dev BDD (Développement)
Phase 4 — Backend core          → Rôle : Dev Backend (Développement)
Phase 5 — Frontend + UI/UX      → Rôles : Dev Frontend + UI/UX (en parallèle)
Phase 6 — QA + DevOps           → Rôles : QA & DevOps (Qualité & Infra)
```

**Dépendances critiques :**
- L'Architecte NE peut PAS travailler sans le GDD
- Le Dev BDD NE peut PAS travailler sans l'architecture
- Le Dev Backend NE peut PAS travailler sans le schéma BDD
- Le Dev Frontend PEUT travailler en parallèle du Backend (sur la base des specs API de l'Architecte)
- Le QA PEUT commencer à écrire ses cas de test dès que le schéma BDD est livré

---

## 4. Ton processus pas à pas pour chaque tâche

### Étape 1 — Lire le handoff reçu
Avant tout, lis attentivement :
- **"Ce que l'agent destinataire doit savoir"** → points d'attention critiques
- **"Prochaine étape suggérée"** → qui travaille ensuite et dans quel ordre

### Étape 2 — Sauvegarder le livrable
Crée un fichier `.md` sur ton ordinateur avec le contenu complet du livrable (handoff + document complet). Nomme-le clairement :

```
gdd.md
architecture.md
schema_bdd.md
HANDOFF_agent7_to_agent5.md
```

### Étape 3 — Uploader dans le(s) bon(s) projet(s)
Va dans chaque projet Claude.ai concerné → icône trombone ou "Ajouter des fichiers" → uploade le fichier.

### Étape 4 — Activer le bon rôle
Ouvre une **nouvelle conversation** dans le projet concerné. Le prompt système du rôle est déjà en place. Si tu dois switcher de rôle dans le même projet, commence la conversation par :

> "Pour cette conversation, tu joues le rôle de l'Agent 3 — Architecte. Voici son prompt système : [colle le prompt]"

### Étape 5 — Briefer le rôle
Dis-lui simplement de lire le fichier dont il a besoin :

> "Lis le fichier `gdd.md` et conçois l'architecture complète du système de vaisseaux d'Emago."

Il lit le fichier uploadé directement — pas besoin de copier-coller le contenu.

### Étape 6 — Valider le livrable
Avant d'accepter un livrable et de passer au suivant, vérifie :
- Le handoff contient-il les 5 sections ? (Contexte / Décisions / Livrable / Ce que l'agent suivant doit savoir / Prochaine étape)
- Les décisions sont-elles justifiées ?
- Les points d'attention pour le prochain rôle sont-ils clairs ?

Si non → demande au rôle de compléter avant de continuer.

### Étape 7 — Passer au rôle suivant
Suis la "Prochaine étape suggérée" du handoff. C'est toujours lui qui te dit où aller.

---

## 5. Comment formuler tes demandes à chaque rôle

### Bonne formulation
> "Lis `gdd.md` et `architecture.md`. En tant qu'Agent 7 (Dev BDD), produis le schéma PostgreSQL complet pour le système de vaisseaux. Inclus les migrations Alembic, les index critiques, et le handoff au format standard."

### Mauvaise formulation
> "Fais le schéma de la base de données."

**La différence :** la bonne formulation précise les fichiers de contexte, le rôle actif, le livrable attendu, et le format de sortie.

---

## 6. Le format handoff standard (à exiger de chaque rôle)

```markdown
---
HANDOFF EMAGO
De : Agent X — [Nom]
À : Agent Y — [Nom]
Sujet : [Titre précis]
Date : [Date]
---

### Contexte reçu
[Ce qui m'a été demandé et les fichiers lus]

### Décisions prises
[Choix effectués avec justification et alternative écartée]

### Livrable
[Le contenu complet du livrable]

### Ce que l'agent destinataire doit savoir
[Points d'attention critiques, contraintes, pièges]

### Prochaine étape suggérée
[Quel rôle travaille ensuite et sur quoi exactement]
---
```

> Si un rôle te produit un livrable sans handoff structuré, demande-lui : *"Reformate ta réponse avec le handoff standard Emago."*

---

## 7. Gestion des fichiers dans VS Code

Tout ce que les rôles Dev produisent atterrit dans ton projet VS Code à l'emplacement exact spécifié. Structure de référence :

```
emago/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   └── models.py              ← Agent 7
│   │   ├── services/
│   │   │   ├── ship_build_service.py  ← Agent 5
│   │   │   ├── ship_stats_service.py  ← Agent 5
│   │   │   ├── combat_engine.py       ← Agent 5
│   │   │   └── forge_service.py       ← Agent 5
│   │   ├── routers/                   ← Agent 5
│   │   └── core/                      ← Agent 5
│   ├── alembic/
│   │   └── versions/
│   │       ├── 0001_initial_schema.py ← Agent 7
│   │       └── 0002_seed_scar_tags.py ← Agent 7
│   └── schema.sql                     ← Agent 7
├── frontend/
│   └── src/
│       └── components/                ← Agent 6
└── docs/
    ├── gdd.md                         ← Agent 2
    ├── architecture.md                ← Agent 3
    ├── schema_bdd.md                  ← Agent 7
    └── handoffs/                      ← Tous les handoffs archivés
```

### Utiliser l'extension Claude dans VS Code
Une fois du code dans VS Code, utilise `@fichier` dans le chat de l'extension pour que Claude vérifie la cohérence :

> "@models.py @ship_build_service.py vérifie que le service est cohérent avec les modèles SQLAlchemy."

> "@workspace est-ce que tous les imports sont cohérents entre le backend et les modèles ?"

---

## 8. Les erreurs à ne jamais faire

| Erreur | Conséquence | Règle |
|---|---|---|
| Coder avant d'avoir le GDD | Tu codes des mécaniques qui changent → tout refare | Phase 1 obligatoire |
| Sauter l'Architecte | Le Backend et le Frontend partent dans des directions incompatibles | Phase 2 obligatoire |
| Uploader dans le mauvais projet | Le rôle n'a pas le contexte, produit des livrables incohérents | Vérifier la table section 2 |
| Accepter un livrable sans handoff | Tu perds le fil, le prochain rôle manque de contexte | Exiger le format standard |
| Copier-coller le contenu au lieu d'uploader | Perte de temps, risque d'erreur | Toujours uploader le fichier |
| Demander à un rôle de travailler hors de son périmètre | Résultats incohérents | Chaque rôle a son prompt système |

---

## 9. Checklist avant de passer à la phase suivante

### Fin de Phase 1 (GDD)
- [ ] Le GDD couvre : ressources, bâtiments, recherches, vaisseaux (classes + rareté + stats RNG + modules + XP), flottes, combats, alliances, classements
- [ ] Les formules d'équilibrage sont définies avec des valeurs chiffrées
- [ ] `gdd.md` est uploadé dans `Emago — Conception` et `Emago — Développement`

### Fin de Phase 2 (Architecture)
- [ ] Tous les endpoints REST sont listés (méthode, path, payload, response)
- [ ] Les événements WebSocket sont définis (direction + payload)
- [ ] La structure des dossiers backend et frontend est spécifiée
- [ ] `architecture.md` est uploadé dans `Emago — Développement` et `Emago — Qualité & Infra`

### Fin de Phase 3 (BDD)
- [ ] Toutes les tables sont créées avec leurs contraintes
- [ ] Le trigger `prevent_base_stats_update` est en place
- [ ] Les index partiels pour les schedulers sont définis
- [ ] Les migrations Alembic sont prêtes (`0001_initial_schema.py`, `0002_seed_scar_tags.py`)
- [ ] Les fichiers sont dans VS Code au bon endroit
- [ ] `schema_bdd.md` et le handoff sont uploadés dans `Emago — Développement`

### Fin de Phase 4 (Backend)
- [ ] `ship_build_service.py` — génération RNG des stats
- [ ] `ship_stats_service.py` — calcul current_stats + cache Redis
- [ ] `combat_engine.py` — résolution combat + XP différentielle
- [ ] `forge_service.py` — scheduler + WS broadcast
- [ ] Tous les endpoints de l'Architecte sont implémentés

### Fin de Phase 5 (Frontend + UI/UX)
- [ ] `<ShipCard />` avec affichage rareté/classe/stats
- [ ] `<ResourceBar />` avec interpolation temps réel
- [ ] `<BuildQueue />` avec countdown
- [ ] `<GalaxyMap />` interactive
- [ ] `<CombatReport />` avec replay

### Fin de Phase 6 (QA + DevOps)
- [ ] Test du trigger `prevent_base_stats_update`
- [ ] Test de la distribution RNG des raretés
- [ ] Test des contraintes UNIQUE et CHECK critiques
- [ ] Docker Compose fonctionnel (api + db + cache + nginx)
- [ ] SSL configuré et WebSocket proxyfié
- [ ] Backup automatique en place

---

## 10. État actuel du projet

| Phase | Statut | Fichiers produits |
|---|---|---|
| Phase 1 — GDD | ✅ Terminé | `gdd.md` |
| Phase 2 — Architecture | ⏳ À démarrer | — |
| Phase 3 — BDD | ✅ Terminé | `schema.sql`, `models.py`, `0001_initial_schema.py`, `0002_seed_scar_tags.py`, `env.py`, `HANDOFF_agent7_to_agent5.md` |
| Phase 4 — Backend | ⏳ À démarrer | — |
| Phase 5 — Frontend + UI/UX | ⏳ À démarrer | — |
| Phase 6 — QA + DevOps | ⏳ À démarrer | — |

> **Prochaine action :** Ouvrir `Emago — Conception`, activer le rôle Architecte (Agent 3), lui faire lire `gdd.md`, et lui demander de concevoir l'architecture complète du système de vaisseaux.

---

*Emago Workflow Guide v1.0 — À mettre à jour après chaque phase terminée*
