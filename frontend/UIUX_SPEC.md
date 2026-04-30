# Emago — Brief UI/UX pour le Designer
> Document destiné à **Agent 4 — UI/UX Designer**
> Le frontend fonctionnel existe déjà. Ce brief concerne l'élévation visuelle : animations, hiérarchie, polish, cohérence.

---

## Contexte et état actuel

Le frontend React/TypeScript est opérationnel avec :
- Dark UI fonctionnelle (`#0a0e1a` background)
- Palette de rareté implémentée (gris/vert/bleu/violet/or)
- Composants : ShipCard, StatBar, ResourceBar, Modal, ForgeProgress, CombatReport
- Navigation sidebar desktop + bottom nav mobile

**Ce qui manque :** le polish visuel qui fait la différence entre "ça marche" et "c'est beau".

---

## 1. Identité visuelle à renforcer

### Référence visuelle
**Mass Effect + Dead Space UI** — non pas cartoonish, non pas flat Windows. C'est :
- Des interfaces qui semblent être *dans* l'univers, pas posées par-dessus
- Des angles, des découpes, des micro-textures technologiques
- Des informations qui *respirent* (whitespace généreux)
- Des couleurs qui *signifient* quelque chose (bleu = info/état, or = précieux/rare)

### Anti-références absolues
- OGame actuel (chargé, tableau HTML brut, années 2000)
- Clash of Clans (cartoonish, coloré, infantilisant)
- Tout ce qui ressemble à un dashboard SaaS B2B

### Palette actuelle (à conserver telle quelle)
```
Surface : #0a0e1a (fond)     #111827 (secondaire)     #1c2333 (tertiaire)
Accents : #2d7dd2 (bleu)     #7c3aed (violet)          #06b6d4 (cyan)
Rareté :  #9E9E9E (commun)   #4CAF50 (peu commun)     #2196F3 (rare)
          #9C27B0 (épique)   #FFD700 (légendaire)
Ressources : #94a3b8 (métal) #7dd3fc (cristal)         #86efac (deutérium)
```

---

## 2. Composants à retravailler visuellement

### 2.1 ShipCard — priorité absolue

C'est l'élément le plus vu du jeu. Il doit communiquer instantanément :

**Problèmes actuels :**
- La bordure colorée est bien mais manque d'impact
- L'icône emoji est placeholder — besoin d'illustrations vectorielles de vaisseaux par classe
- Les stats (hull/dps/speed) en bas manquent de lecture rapide

**Ce qu'il faut :**
- **Background dégradé subtil** par classe : rouge/noir pour ATTACK, bleu/noir pour DEFENSE, vert/noir pour SUPPORT, violet/noir pour EXPLORATION
- **Silhouette de vaisseau SVG** par classe (pas par rareté) — simple, géométrique, Mass Effect style
- **Badge rareté redesigné** : hexagone ou forme angulaire, pas rectangle arrondi
- Pour LEGENDARY : animation de particules dorées très subtile (3-5 particules flottantes, CSS only)
- **Micro-highlight** : fine ligne lumineuse sur le bord supérieur de la carte, couleur = rareté

**Specs techniques :**
- Taille minimum : 160px × 200px (mobile) / 200px × 240px (desktop)
- Doit fonctionner en grid 1, 2 et 3 colonnes
- État sélectionné : ring + scale(1.02)
- État hover : très léger glow (pas d'animation lourde)

---

### 2.2 Barres de stats (StatBar)

**Actuellement :** barre plate colorée. C'est fonctionnel mais générique.

**Ce qu'il faut :**
- Fond de la barre en segments (style tech), pas plein
- Remplissage avec gradient directionnel (plus lumineux à l'extrémité active)
- Animation de remplissage au premier affichage (slide depuis 0)
- Si `cap_reached` : la barre doit être orange avec une icône 🔒 et une micro-animation de "débordement"
- Les labels devraient avoir des icônes personnalisées SVG (pas emoji) : cœur pixelisé pour hull, bouclier pour shield, etc.

---

### 2.3 ResourceBar — barre de ressources planète

**C'est l'élément consulté le plus fréquemment.**

**Ce qu'il faut :**
- Icônes distinctives SVG pour métal (lingot), cristal (gemme 6 faces), deutérium (atome/flamme)
- Le chiffre qui s'incrémente visuellement (counter animation de date-fns → custom hook) — actuellement c'est déjà interpolé, ajouter le `transition-all` sur les chiffres
- Quand plein (>95%) : la barre doit pulse orange pour alerter "stockage saturé"
- Taux de production (+X/h) plus visible — actuellement très petit

**Layout suggéré :**
```
[icône métal]  [valeur grande]    [+1234/h]
               [████████░░░░░]  78%
```

---

### 2.4 Navigation sidebar

**Ce qu'il faut :**
- Icônes SVG propres (pas emoji) pour chaque section
- Item actif : fond avec clip-path diagonal gauche (style "tab cassée")
- Bordure gauche lumineuse sur l'item actif (3px, couleur accent-blue)
- Logo "EMAGO" avec une typo condensée, les deux lettres différentes (EM en blanc, AGO en bleu)
- Indicateur WS connecté plus visible — petit globe animé, pas juste un point

**Mobile (bottom nav) :**
- Hauteur minimum 64px pour le touch
- L'item actif a un indicateur en haut (pas en bas comme iOS)
- Animation tap : ripple léger

---

### 2.5 ForgeProgress — barre de forge

**Le joueur attend 8h — c'est une mécanique d'engagement.**

**Ce qu'il faut :**
- Illustration d'une forge/fourneau stylisée en arrière-plan (SVG très épuré, opacité 10%)
- Progress bar avec effet "lava" ou "forge" : gradient orange→rouge qui se déplace
- Le temps restant affiché en grand (HH:MM:SS), police monospace
- Quand terminé : animation flash doré + particules (1-2 secondes, CSS keyframes)
- Notification toast redesignée quand la forge se termine (icône + rareté résultante colorée)

---

### 2.6 CombatReport (modal)

**C'est le moment de drama du jeu.**

**Ce qu'il faut :**
- Fond modal : image de fond étoilée très sombre (opacité 20-30%) avec effet de champ de débris
- Header VICTOIRE/DÉFAITE : grande typo avec couleur + ombre correspondante
- Victoire : teinte verte douce, étoile animée
- Défaite : teinte rouge, effet "brisé" (crack SVG très subtil derrière le texte)
- Les pertes (vaisseaux détruits) : liste avec icône vaisseau barré en rouge
- Animation d'entrée : slide-up + fade, 300ms

---

## 3. Écrans à concevoir (pas encore existants)

### 3.1 GalaxyPage — carte galactique

**C'est l'écran le plus ambitieux visuellement.**

Inspiration : Mass Effect galaxy map (fond noir, étoiles ponctuelles, lignes de systèmes)

**Éléments :**
- Grille hexagonale ou circulaire de systèmes stellaires
- Chaque système = cercle coloré selon son occupation (neutre/joueur/ennemi)
- Zoom in/out sur un système pour voir les planètes (1-15 positions)
- Position des flottes en transit : ligne pointillée animée entre deux planètes avec un petit vaisseau qui se déplace
- Tooltip au hover : propriétaire, nb de vaisseaux, ressources si espionné

**Ce qui ne doit PAS être dessiné pour l'instant :**
- La carte 3D interactive (trop complexe, phase 3)
- Des illustrations de planètes réalistes (coût > valeur)

**Alternative réaliste phase 1 :**
- Grille 9×499 (galaxies × systèmes) stylisée comme un terminal spatial
- Chaque cellule = un point lumineux avec hover
- Sélection filtrée par galaxie (dropdown)

---

### 3.2 Dashboard planète — vue d'ensemble

**L'écran d'accueil quotidien du joueur.**

Layout suggéré (desktop, 2 colonnes) :
```
┌─────────────────────┬──────────────────┐
│  ResourceBar        │  Forges actives  │
│  (métal/cristal/    │  (progress bars) │
│   deutérium)        │                  │
├─────────────────────┼──────────────────┤
│  Vaisseaux récents  │  Activité récente│
│  (3 ShipCards)      │  (timeline)      │
└─────────────────────┴──────────────────┘
```

Mobile : tout en colonne, ResourceBar en haut sticky.

---

### 3.3 Écran de connexion / inscription

**Première impression — doit donner envie.**

**Ce qu'il faut :**
- Fond : champ d'étoiles animé CSS (particules lentes, pas de canvas JS)
- Nébuleuse colorée en arrière-plan (gradient radial violet/bleu, opacité 15%)
- Logo EMAGO en grand avec micro-animation d'apparition
- Form card centrée avec glassmorphism très léger (`backdrop-blur-sm`, bg opacité 80%)
- Bouton de connexion avec gradient et hover glow

---

## 4. Système de design à formaliser

### Typographie
- **Titres d'écran** : 24-28px, font-weight 700, tracking tight
- **Labels** : 12px uppercase, letter-spacing 0.1em, text-gray-400
- **Valeurs de stats** : font-mono, font-weight 600 (chiffres dans les barres)
- **Corps** : 14-16px, font-weight 400, line-height 1.6

### Espacements
- Padding interne des cards : 16px mobile / 20px desktop
- Gap entre cards : 12px mobile / 16px desktop
- Margin de section : 24px

### Ombres et profondeur
- Cards au repos : aucune ombre (flat design)
- Cards au hover : `shadow-lg` couleur sombre (pas la couleur de rareté)
- Modals : `shadow-2xl` + backdrop blur

### Animations — règles strictes
- **Durée max** : 300ms pour les interactions, 600ms pour les transitions de page
- **Easing** : `ease-out` pour les entrées, `ease-in` pour les sorties
- **Jamais** : rotate sans raison, bounce excessif, parallax agressif
- **Autorisé** : fade, slide-up, scale légère (1.00 → 1.02), glow pulse lent (3-4s)
- **Respecter** : `prefers-reduced-motion` — toutes les animations doivent se désactiver

### États
- **Loading** : skeleton shimmer (déjà implémenté)
- **Error** : panel rouge avec icon d'alerte + message serveur
- **Empty** : illustration SVG simple + message + CTA
- **Success** : toast vert en haut à droite (react-hot-toast)
- **Disabled** : opacité 40%, cursor not-allowed

---

## 5. Livrables attendus de l'Agent 4

### Format de livraison
- Composants Tailwind + inline styles (pas de Figma requis — directement du code)
- Ou Figma si vous préférez, mais les variables CSS Tailwind doivent être respectées

### Priorité 1 (bloquant pour le jeu jouable)
1. `ShipCard` redesignée avec silhouettes SVG par classe
2. `ResourceBar` avec icônes SVG et layout amélioré
3. Écran de connexion soigné (première impression)

### Priorité 2 (polish)
4. `StatBar` avec animations d'entrée
5. `ForgeProgress` avec illustration forge
6. `CombatReport` modal dramatisée

### Priorité 3 (phase 2)
7. `GalaxyPage` — carte interactive
8. Dashboard restructuré 2 colonnes
9. Icons set SVG complet (remplacement des emojis)

---

## 6. Contraintes techniques à respecter

- **Tailwind CSS uniquement** pour les styles — pas de CSS-in-JS, pas de styled-components
- **Mobile-first** — tout doit fonctionner sur 375px de large sans scroll horizontal
- **Pas de bibliothèques UI lourdes** (pas de MUI, pas de Chakra)
- **Animations CSS uniquement** — pas de GSAP, pas de Framer Motion (trop lourd pour un jeu)
- Les couleurs de rareté sont définies dans `tailwind.config.js` sous `theme.extend.colors.rarity` — les utiliser exactement
- Le `dark:` variant n'est pas nécessaire — le jeu est dark-only

---

## 7. Inspiration concrète (screenshots mentaux)

**Pour les ShipCards :** imaginez les cartes de personnage dans Mass Effect Legendary Edition — icon de classe en haut à gauche, barre de "level" fine en bas, fond légèrement texturé selon la faction.

**Pour la ResourceBar :** imaginez les HUD de StarCraft 2 — chaque ressource a une icône 3D rendue plate, le chiffre est grand et se met à jour en temps réel.

**Pour la Forge :** imaginez la salle de craft de Dark Souls — une enclume dans un espace sombre, des étincelles, une attente pesante et satisfaisante.

**Pour les Modals de combat :** imaginez les écrans de fin de combat de X-COM — résultats clairs, récompenses mises en avant, pertes présentées avec sobriété.
