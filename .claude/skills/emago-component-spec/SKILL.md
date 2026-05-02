---
name: emago-component-spec
description: Rédige la spécification UI/UX d'un composant React réutilisable Emago (ShipCard, ResourceBar, badge rareté, modal, countdown, panel espionnage…) en respectant le design system — palette rareté canonique, dark UI Mass Effect, Tailwind classes existantes, mobile-first 375px+. Produit un document de spec destiné à Agent 6 (Dev Frontend). Met à jour docs/04_uiux_designer.md section catalogue composants. Use when l'utilisateur dit "spec composant Emago", "design composant", "spec ShipCard améliorée", "comment doit s'afficher X", "maquette composant", "spec UI badge".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 4-uiux-designer
---

# emago-component-spec

Rédige des spécifications de composants Emago précises et cohérentes avec le design system. Sert de brief pour Agent 6 (Dev Frontend) avant l'implémentation.

---

## Quand utiliser ce skill

- Spécifier un nouveau composant réutilisable avant que Agent 6 le code.
- Documenter un composant existant pour clarifier son comportement attendu.
- Refondre un composant existant (nouvelle spec avant refactoring).

## Quand NE PAS utiliser ce skill

- Pour une page entière → utilise `emago-screen-spec`.
- Pour coder le composant → utilise `emago-component-scaffold` (Agent 6).
- Pour valider qu'un composant respecte le design system → effectuer une revue visuelle directe.

---

## Instructions

### Étape 1 — Cadrer le composant

Pose à l'utilisateur :
1. **Nom** (PascalCase, ex. `ProbeReportCard`, `AllianceTag`, `ScarBadge`).
2. **Contexte d'usage** : dans quelles pages ou autres composants sera-t-il utilisé ?
3. **Donnée principale** : quel objet métier affiche-t-il (Ship, Alliance, EspionageReport…) ?
4. **Actions possibles** : clics, expands, toggles, callbacks.
5. **Variantes** : tailles (compact, normal, large), états (actif, inactif, loading).

### Étape 2 — Vérifier le catalogue existant

Lire `docs/04_uiux_designer.md` section 8 (catalogue composants) :
- Le composant existe-t-il déjà ? (éviter les doublons).
- Un composant similaire peut-il être étendu plutôt que recréé ?
- Quelles props seraient rétrocompatibles si extension d'un existant ?

### Étape 3 — Embarquer le design system

**Palette obligatoire** :

| Usage | Couleur | Classe Tailwind |
|---|---|---|
| Fond panneaux | `rgba(13,18,30,0.85)` | `.panel` |
| Bordures | `rgba(35,50,70,0.8)` | `.border-border` |
| Texte principal | blanc / gris clair | `text-white / text-gray-300` |
| Accent action | `#2d7dd2` | `text-blue-400` |
| Succès / green | `#10b981` | `text-green-400` |
| Alerte / orange | `#f97316` | `text-orange-400` |
| Danger | rouge | `text-red-400` |
| COMMON | `#9E9E9E` | `text-gray-400` |
| UNCOMMON | `#4CAF50` | `text-green-400` |
| RARE | `#2196F3` | `text-blue-400` |
| EPIC | `#9C27B0` | `text-purple-400` |
| LEGENDARY | `#FFD700` | `text-yellow-400` |

**Typographie** :
- Labels section / titres : Orbitron uppercase (`font-display tracking-widest uppercase text-xs`).
- Texte courant : Inter (`font-sans`).
- Stats numériques : JetBrains Mono (`font-mono`).

**Animation** : subtile ≤ 0.3s sauf overlays narratifs (RarityReveal, SpectreAwakening).

### Étape 4 — Rédiger la spec du composant

Structure obligatoire :

```markdown
## Composant : <Name>

**Localisation cible** : `components/<feature>/<Name>.tsx`
**Utilisé dans** : [pages ou composants parents]
**Dépendances** : [types TypeScript requis, stores Zustand]

### Props

| Prop | Type | Requis | Description |
|---|---|---|---|
| field | Type | ✓ | Description |
| onAction | (v: T) => void | ✗ | Callback optionnel |

### Layout

[Description textuelle + ASCII mockup si utile]

### Variantes

- **Compact** : [description]
- **Normal** : [description]
- **Large** : [description, si applicable]

### États

- **Normal** : [description]
- **Loading** : skeleton `animate-pulse` sur les éléments dynamiques
- **Vide** : [texte placeholder]
- **Erreur** : badge rouge discret, pas de crash

### Interactions

| Action | Déclencheur | Effet |
|---|---|---|
| Clic | `onClick` | [effet visuel + callback] |
| Hover | CSS `hover:` | [highlight couleur accent] |

### Animations

- Apparition : `animate-fade-in` 0.3s
- [Autres si applicable]

### Mobile-first

- 375px : [disposition]
- sm: 640px : [disposition]
- md: 768px+ : [disposition finale]

### Notes pour Agent 6

- Types à créer/importer : [liste]
- Stores Zustand à utiliser : [liste]
- Query TanStack si data fetching local : [clé + url]
```

### Étape 5 — Valider la cohérence

Avant de livrer :
- ☐ Aucune couleur hors palette.
- ☐ Palette rareté respectée si le composant affiche un vaisseau.
- ☐ Pas de pop-up intrusif (modal uniquement si action critique).
- ☐ Animation ≤ 0.3s.
- ☐ Mobile-first : tout s'affiche à 375px sans overflow.
- ☐ État loading pensé.
- ☐ État vide pensé avec message utile.

### Étape 6 — Mettre à jour `docs/04_uiux_designer.md` (obligatoire)

- Section 8 (catalogue composants) : ajouter le nouveau composant avec description + localisation.
- Si modification d'un composant existant : mettre à jour sa ligne dans le tableau.

---

## Examples

### Exemple 1 — ScarBadge (badge cicatrice vaisseau)

**User** : "Spec le composant ScarBadge pour afficher une cicatrice narrative sur ShipCard"

**Résultat** :
- Props : `scar: { tag_code: string, narrative: string }`, `size?: 'xs' | 'sm'`.
- Layout : badge pill avec icône épée stylisée + texte `narrative` tronqué à 20 chars.
- Couleur : `text-amber-400 border-amber-600 bg-amber-950/30`.
- Hover : tooltip avec narrative complète.
- Compact : juste l'icône + nombre si `size="xs"`.
- Mobile : identique normal (badge reste lisible à 375px).
- Notes Agent 6 : type `ShipScar` déjà dans `types/index.ts`, pas de nouveau type requis.

### Exemple 2 — AllianceTag (badge alliance sur profil)

**User** : "Spec AllianceTag, le badge [TAG] d'alliance affiché sur les profils joueurs"

**Résultat** :
- Props : `tag: string`, `color?: string` (défaut `#2196F3`).
- Layout : `[TAG]` en Orbitron bold, carré arrondi, bordure couleur alliance.
- Taille unique (`sm`), pas de variante large.
- Tooltip optionnel avec le nom complet de l'alliance au hover.
- Mobile : taille fixe 32px, ne tronque pas.

### Exemple 3 — Extension ShipCard avec cicatrices

**User** : "Modernise la spec de ShipCard pour inclure les cicatrices"

**Actions** :
1. Lit la spec actuelle de ShipCard dans `docs/04_uiux_designer.md`.
2. Ajoute prop `scars?: ShipScar[]` (optionnel, 0-5 cicatrices max).
3. Section "Cicatrices" sous les stats : ligne de ScarBadge en taille xs.
4. Si > 3 cicatrices : "+N de plus" en lien hover.
5. Note Agent 6 : réutiliser le nouveau composant `ScarBadge`.

---

## Troubleshooting

### Le composant fait doublon avec un existant

**Cause** : catalogue pas lu avant la spec.
**Solution** : toujours vérifier `docs/04_uiux_designer.md` section 8. Si doublon → étendre l'existant avec nouvelles props plutôt que créer.

### Spec trop vague pour Agent 6

**Cause** : pas de détail sur les props TypeScript ou les sources de données.
**Solution** : finir par "Notes pour Agent 6" avec liste types, stores, queries.

### Couleurs inventées hors palette

**Solution** : utiliser uniquement les classes Tailwind autorisées. Jamais de hex inline dans la spec.

---

## References

- `references/design_system.md` — palette, typographie, classes Tailwind Emago.
- `references/component_catalog.md` — catalogue des composants existants.
- `references/component_spec_template.md` — template markdown complet de spec composant.
