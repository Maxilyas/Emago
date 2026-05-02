---
name: emago-screen-spec
description: Rédige une spécification UI/UX complète pour un nouvel écran Emago en respectant le design system du projet — palette de rareté canonique (#9E9E9E COMMON / #4CAF50 UNCOMMON / #2196F3 RARE / #9C27B0 EPIC / #FFD700 LEGENDARY), dark UI Mass Effect, typographie Orbitron + Inter + JetBrains Mono, classes Tailwind .panel/.btn-primary/.input-field, animations subtiles, mobile-first 375px+. Sortie un markdown avec layout, composants, états, API endpoints, events WS, interactions, animations. Use when l'utilisateur dit "spec écran Emago", "design page espionnage", "concevoir UI marché galactique", "écran profil joueur", "UX page X".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 4-uiux-designer
---

# emago-screen-spec

Rédige des specs UI/UX d'écran Emago cohérentes avec le design system du projet. Garantit la cohérence visuelle entre tous les écrans en embarquant la palette, la typographie et les patterns existants.

---

## Quand utiliser ce skill

- Concevoir un nouvel écran (page Profil, page Espionnage, page Marché galactique…).
- Documenter un écran existant pour clarifier son comportement (sert de spec de référence pour Agent 6).
- Refondre un écran existant (recommencer la spec proprement avant impl).

## Quand NE PAS utiliser ce skill

- Pour un composant isolé (ShipCard, Badge…) → utilise `emago-component-spec`.
- Pour valider qu'une page existante respecte le design system → effectuer une revue visuelle directe ou utiliser `emago-attack-vector-audit` pour la partie sécurité.
- Pour le code React lui-même → utilise `emago-page-scaffold`.

---

## Instructions

### Étape 1 — Cadrer l'écran

Pose à l'utilisateur :

1. **Nom de l'écran** + route React Router (ex. `/espionage` → `EspionagePage`).
2. **Audience** : tous joueurs / membres alliance / leader / autres ?
3. **Objectif principal** : qu'est-ce que le joueur doit pouvoir faire en arrivant ?
4. **Données affichées** : quelles ressources serveur (endpoints API existants ou à créer) ?
5. **Events temps réel** : reçoit des messages WebSocket ? Lesquels ?
6. **Interactions principales** : 3 actions clés que le joueur peut faire.
7. **Densité** : compact (Dashboard) ou immersif (Galaxy/Forge) ?

### Étape 2 — Vérifier l'existant

Regarde dans `references/existing_screens.md` les écrans déjà spécifiés. Pour chaque écran similaire :
- Reprendre les patterns de layout (sidebar gauche / hero + grid / tabs).
- Réutiliser les composants existants (`ShipCard`, `ResourceBar`, `BuildingCardUX`, etc.).
- S'aligner sur les durées d'animation (`fade-in` 0.3s, `slide-up` 0.25s).

### Étape 3 — Embarquer le design system

Toujours appliquer ces règles (cf. `references/design_system.md`) :

**Palette obligatoire** :
- Fond `--void: #050810`, panneaux `--panel: rgba(13,18,30,0.85)`, bordures `--border: rgba(35,50,70,0.8)`.
- Couleurs accent : blue `#2d7dd2`, violet `#7c3aed`, cyan `#06b6d4`, green `#10b981`, orange `#f97316`.
- Couleurs ressources : metal `#94a3b8`, crystal `#7dd3fc`, deuterium `#86efac`, energy `#fbbf24`.
- **Rareté** (jamais autre couleur pour communiquer la rareté) : `#9E9E9E / #4CAF50 / #2196F3 / #9C27B0 / #FFD700`.

**Typographie** :
- Titres section / labels : Orbitron uppercase letter-spacing 0.15em via classe `.section-title` ou `font-display`.
- Texte courant : Inter (font-sans).
- Stats numériques : JetBrains Mono.

**Classes Tailwind & composants existants** :
- `.panel`, `.panel-glass`, `.panel-glow` pour les conteneurs.
- `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-ghost` — toujours scale-95 on active.
- `.input-field` avec focus ring bleu accent.
- `.glow-{rarity}` pour halo selon rareté.
- `.animate-fade-in` (page-level), `.animate-slide-up` (modals), `.animate-pulse` (badges actifs).

**Mobile-first** :
- Tous les composants doivent tenir à 375 px de largeur.
- Breakpoints Tailwind : `sm:` 640px, `md:` 768px, `lg:` 1024px.

### Étape 4 — Rédiger la spec

Utilise `references/spec_template.md`.

Structure obligatoire :
1. **Métadonnées** : nom, route, agents impactés, dépendances API/WS.
2. **Layout général** (texte + ASCII mockup si pertinent).
3. **Composants** (réutilisés + nouveaux à créer).
4. **États** : Normal / Chargement / Vide / Erreur / (le cas échéant) Succès.
5. **Données nécessaires** : payload API requis + events WS.
6. **Interactions** : table action → effet → endpoint.
7. **Animations** : liste avec durée et trigger.
8. **Accessibilité** : focus order, contraste, aria-labels.
9. **Notes mobile-first** : adaptations sm: / md: / lg:.
10. **Notes pour Agent 6** : composants à créer, hooks à utiliser, query keys.

### Étape 5 — Valider la cohérence

Avant de livrer :
- ☐ Aucune couleur hors palette (sauf justification explicite).
- ☐ Au moins une référence à la palette de rareté si vaisseaux affichés.
- ☐ Aucun pop-up intrusif (privilégier sidepanels et overlays doux).
- ☐ Animations subtiles (≤ 0.5s sauf overlays narratifs RarityReveal/SpectreAwakening).
- ☐ Mobile-first considéré (375px tient ?).
- ☐ État vide pensé (`<EmptyState>` avec CTA si action possible).
- ☐ État chargement pensé (skeletons, pas spinner full-screen).

### Étape 6 — Mettre à jour `docs/04_uiux_designer.md`

Ajouter le nouvel écran à la table section 7 ("Catalogue des écrans"). Si nouveau composant créé, l'ajouter à la table section 8.

---

## Examples

### Exemple 1 — Page d'espionnage

**User** : "Spec UX pour la page espionnage : envoyer une sonde, voir résultats, voir détection adverse"

**Actions** :
1. Cadrer : route `/espionage`, audience tous joueurs, données : sondes lancées, rapports reçus, niveau détection. Events WS : `espionage.report_ready`.
2. Layout proposé : header + 3 panneaux (lancer sonde / mes rapports / détections sur moi).
3. Composants : `ShipCard` (compact pour sélection sonde), nouveau `<ProbeReportCard>` (à spécifier), `<DetectionAlert>` (badge rouge sur sidebar).
4. États vides : "Aucune sonde envoyée — choisis une cible" avec CTA "Voir Galaxy".
5. Animations : `slide-up` modal sélection cible, `pulse` sur badge nouvelle détection.
6. Mobile : panneaux empilés vertical, sélection cible plein écran modal.

### Exemple 2 — Page Profil joueur

**User** : "Concevoir l'écran Profil avec stats globales et historique combats"

**Actions** :
1. Layout : hero (avatar + username + score + rang) ; tabs Stats / Combats / Vaisseaux glorieux / Alliance.
2. Sections : 4 stats clés (top, victoires, vaisseaux Spectre, expéditions exceptionnelles), liste combats récents (limit 20), top 3 vaisseaux légendaires détaillés.
3. Réutilise `<ShipCard>` pour vaisseaux, `<CombatReport>` mini pour historique.
4. Note Agent 6 : nouvelle query `/players/{id}/profile` (existe pas → flag à Agent 5).
5. Validation : palette OK, pas de pop-ups, mobile vertical OK.

### Exemple 3 — Refonte d'écran existant

**User** : "Reprends la spec de la page Hangar, je veux la moderniser"

**Actions** :
1. Charge la spec actuelle depuis `docs/04_uiux_designer.md` section 7 + `docs/06_dev_frontend.md` section 7 `HangarPage.tsx`.
2. Identifie les écarts vs design system actuel (si modifs UX).
3. Rédige la nouvelle spec en marquant les changements vs version actuelle.
4. Liste les composants existants à modifier vs nouveaux à créer.

---

## Troubleshooting

### Les couleurs proposées ne sont pas dans la palette

**Cause** : tendance à inventer des couleurs pour différencier des sections.
**Solution** : utiliser les variations Tailwind autorisées (gray-400 à gray-900, sky-400…) ou les couleurs accent existantes (blue/violet/cyan/green/orange) — JAMAIS d'autre teinte.

### Composant proposé existe déjà

**Cause** : ne pas avoir consulté la liste des composants existants.
**Solution** : toujours lire `docs/04_uiux_designer.md` section 8 (catalogue composants) avant de proposer un nouveau.

### Le mobile-first n'est pas tenable

**Cause** : trop d'info à afficher en 375px.
**Solution** : prioriser hiérarchiquement, masquer les infos secondaires derrière un toggle ou tab. Si impossible, accepter un breakpoint min `sm:` (640px) explicite.

### Spec trop vague pour Agent 6

**Cause** : pas de détail sur query keys TanStack ni events WS.
**Solution** : toujours finir par "Notes pour Agent 6" listant : queries (key + url + interval), mutations (key + url + invalidate), events WS (handlers).

---

## References

- `references/spec_template.md` — template markdown complet.
- `references/design_system.md` — palette, typo, classes Tailwind, animations Emago (extraits de `docs/04_uiux_designer.md`).
- `references/existing_screens.md` — catalogue des 14 écrans existants pour réutilisation patterns.
- `references/component_catalog.md` — composants disponibles à réutiliser.
