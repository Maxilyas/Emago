# Emago — Guide du joueur

> Bienvenue, capitaine. Ce guide explique tout ce qu'il faut savoir pour démarrer ta carrière de stratège galactique sans effort.

---

## 1. Qu'est-ce qu'Emago ?

**Emago** est un jeu de stratégie spatiale en temps réel jouable par navigateur. Tu commences avec une planète natale, tu produis des ressources, tu construis des bâtiments et des vaisseaux, tu explores la galaxie, tu te bats, tu rejoins une alliance, tu domines.

Particularité : **chaque vaisseau que tu construis est unique.** Il a sa propre rareté, ses propres stats (générées au hasard), son propre nom (à partir de RARE), son propre trait, et accumule cicatrices et expérience au fil de ses combats.

**Notre promesse** : aucune mécanique pay-to-win. Tu progresses par ton intelligence tactique, pas par ton portefeuille.

---

## 2. Lore / Univers

L'humanité a quitté la Terre il y a longtemps. Les survivants se dispersent dans 9 galaxies, organisées en 499 systèmes stellaires, eux-mêmes divisés en 15 positions orbitales. Chacun cultive sa propre planète, fonde son chantier naval, développe ses technologies, et contemple les étoiles avec ambition.

Mais l'espace est vaste, dangereux, et plein de surprises. Les ruines spatiales (debris fields, derelict stations) abritent des artefacts inestimables. Les nébuleuses radioactives marquent ceux qui les traversent. Les pirates rôdent sur les routes. Et parfois, dans un éclat de pure chance, un vaisseau sort de votre Forge avec une **Dérive** — un défaut narratif qui le rend imparfait, mais inoubliable.

Les **alliances** sont la clé pour les ambitions plus grandes : se regrouper pour défendre, conquérir, déclarer la guerre. Mais une alliance limite à 20 membres force la cohésion : pas de méga-clans, juste des bandes soudées.

---

## 3. Premiers pas

### Inscription

1. Va sur la page de connexion → onglet "INSCRIPTION".
2. Choisis un username (3-32 caractères, lettres/chiffres/underscores).
3. Email + mot de passe (≥ 8 caractères).
4. Clique "Créer un compte" → tu reçois automatiquement une planète natale (homeworld) à des coordonnées aléatoires.

### Premier coup d'œil

Tu arrives sur le **Dashboard** :
- Ton **rang** dans le classement (à droite).
- Ton **Daily Panel** : récompense de connexion + 3 missions du jour.
- Ta **planète natale** avec stocks de ressources (métal, cristal, deutérium).
- Tes flottes en transit (vide au début).
- Tes forges en cours (vide).
- L'activité récente (vide).

### Premières actions recommandées

1. **Construire une Mine de métal niveau 2** (depuis `Bâtiments`). Le métal est ta ressource n° 1 au début.
2. **Construire un Chantier Naval niveau 1** (Mines doivent être niv 2 pour le déverrouiller).
3. **Construire ton premier vaisseau** : `frigate_attack` (3 000 métal + 1 000 cristal). Tirage RNG → tu pourrais tomber sur un Légendaire (1 % de chance) !
4. **Lance une expédition courte** (2 h) avec ton premier vaisseau pour goûter au système d'événements.
5. **Réclame ta récompense Daily** chaque jour pour entretenir ton streak.

---

## 4. Les ressources

### Métal, cristal, deutérium

Tes 3 ressources principales. Produites en continu par tes mines :
- **Mine de métal** : production de base 30/h × niveau × 1.1^niveau.
- **Usine de cristal** : 15/h × niveau × 1.1^niveau.
- **Synthétiseur de deutérium** : 5/h × niveau × 1.1^niveau (et nécessite plus d'énergie).

### Énergie

L'**Usine d'énergie solaire** alimente tes mines. Si la production d'énergie est insuffisante, tes mines tournent au ralenti (`energy_factor < 1.0`). Vérifie le panneau ⚡ ÉNERGIE de la page Bâtiments.

### Capacités

Chaque planète a une capacité maximale de stockage :
- 10 000 métal
- 10 000 cristal
- 5 000 deutérium

Au-delà, la production stocke jusqu'au cap puis stagne. Construis des **entrepôts** plus grands (Phase 2) ou consomme régulièrement.

---

## 5. Les bâtiments

| Bâtiment | Rôle |
|---|---|
| **Mine de métal** | Produit du métal |
| **Usine de cristal** | Produit du cristal |
| **Synthétiseur deutérium** | Produit du deutérium (gros besoin énergie) |
| **Usine d'énergie solaire** | Alimente les mines |
| **Chantier naval** | Permet de construire des vaisseaux. Niveau requis : 1 (frégates), 2 (exploration), 4 (croiseurs) |
| **Laboratoire de recherche** | Permet d'effectuer des recherches technologiques |

Coût d'un upgrade : **× 1.5 par niveau**. Niveau 5 d'un bâtiment coûte donc `1.5^5 = 7.6×` le coût initial.

---

## 6. Les vaisseaux

### Les 4 classes

| Classe | Rôle | Stats forte |
|---|---|---|
| **ATTACK** | Tueur de DPS | DPS très élevé, hull faible |
| **DEFENSE** | Tank | Hull et shield énormes, DPS faible |
| **SUPPORT** | Médecin / amplificateur | Aura de soutien, faible DPS |
| **EXPLORATION** | Vitesse / cargo / furtivité | Très rapide, gros cargo, peu de combat |

Une flotte mono-classe est toujours vulnérable à quelque chose. Combine pour des **synergies** :
- **ATTACK + SUPPORT** → +20 % DPS pour les attackers.
- **DEFENSE + SUPPORT** → +5 % hull/round.
- **DEFENSE × 3+** → +15 % shield collectif.
- **ATTACK + EXPLORATION ≥ 20 %** → +10 % vitesse de flotte.

### Les 6 types de vaisseaux

| Type | Classe | Coût (M/C/D) | Chantier requis |
|---|---|---|---:|
| frigate_attack | ATTACK | 3 000 / 1 000 / 0 | 1 |
| frigate_defense | DEFENSE | 6 000 / 2 000 / 0 | 1 |
| frigate_support | SUPPORT | 2 000 / 2 000 / 500 | 1 |
| frigate_exploration | EXPLORATION | 2 000 / 1 000 / 1 000 | 2 |
| cruiser_attack | ATTACK | 20 000 / 7 000 / 2 000 | 4 |
| cruiser_defense | DEFENSE | 30 000 / 10 000 / 2 000 | 4 |

### Les 5 raretés

À chaque construction, le serveur tire une rareté au hasard :

| Rareté | Couleur | Probabilité | Multi stats | Slots modules |
|---|---|---:|---:|---:|
| **Commun** | Gris | 55 % | × 1.00 | 2 |
| **Peu commun** | Vert | 27 % | × 1.25 | 3 |
| **Rare** | Bleu | 12 % | × 1.55 | 4 (1 premium) |
| **Épique** | Violet | 5 % | × 1.90 | 5 (2 premium) |
| **Légendaire** | Or | 1 % | × 2.40 | 6 (3 premium) |

> **Slots premium** : derniers slots (badge or). Acceptent les modules niveau IV et V (les plus puissants).
>
> **Petit coup de chance ?** Un Légendaire chanceux peut être plus puissant qu'un Épique malchanceux. Mais le plancher d'un Légendaire reste largement supérieur à un Épique moyen.

### Variance ±10 %

À l'intérieur d'une rareté, les stats varient de ±10 %. Deux Légendaires du même type ont rarement les mêmes stats — un Légendaire mal tiré peut être moins fort qu'un Épique chanceux.

### Nom procédural (RARE+)

Les vaisseaux **Rare et plus** reçoivent un nom unique au format `[Racine] [Qualificatif]` :
- *Astraeus Noir* (ATTACK)
- *Eryndor Inébranlable* (DEFENSE)
- *Kha Lumineux* (SUPPORT)
- *Vael Errant* (EXPLORATION)

Avec 80 racines × 15 qualificatifs par classe, la chance de doublon est de 1/1200.

### Trait narratif

**Tous les vaisseaux** reçoivent un trait à la construction (~200 traits dans 8 familles). Le trait donne un petit bonus permanent (+5 à +16 %) sous certaines conditions :
- **ALWAYS** : tout le temps actif.
- **SOLO** : actif uniquement si le vaisseau combat seul.
- **FLEET_3PLUS** : actif si flotte ≥ 3 vaisseaux.
- **CLASS_MATCH** : actif si la classe correspond.

Exemples :
- **Chasseur de Primes** (SOLO) : +10 % DPS quand il chasse seul.
- **Âme d'Équipage** (FLEET_3PLUS) : +8 % DPS pour TOUS les alliés en flotte de 3+.
- **Doctrine d'Assaut** (CLASS_MATCH ATTACK) : +10 % DPS si ATTACK.

---

## 7. Les modules

Tu peux installer jusqu'à 6 modules sur tes vaisseaux (selon rareté). Chaque module boost une stat :

| Module | Boost | Affinité (×1.15 si même classe) |
|---|---|---|
| **PROPELLER** | speed | EXPLORATION |
| **ARMOR** | hull | DEFENSE |
| **CANNON** | dps | ATTACK |
| **EMITTER** | support_aura | SUPPORT |
| **SHIELD** | shield | DEFENSE |
| **CARGO** | cargo | EXPLORATION |

Les boosts varient de **+8 % à +44 %** selon le niveau (I-V). Les niveaux IV et V ne s'installent que dans les **slots premium** (raretés Rare+).

> **Cap absolu : +150 % par stat.** Empiler 6 CANNON niveau V sur un vaisseau ATTACK ne permettra pas de dépasser 2.5× la stat de base. L'UI marque les stats plafonnées avec une icône 🔒.

---

## 8. Les grades XP

Chaque combat fait gagner de l'XP à tes vaisseaux survivants. L'XP débloque des **grades** apportant des bonus passifs permanents :

| Grade | Nom | XP | Bonus |
|---|---|---:|---|
| 0 | Recrue | 0 | — |
| 1 | Vétéran | 500 | +5 % toutes stats |
| 2 | Élite | 2 000 | +10 % toutes stats |
| 3 | Légion | 6 000 | +15 % toutes stats, régén 2 % bouclier/round |
| 4 | Légende | 15 000 | +22 % toutes stats, **immunité à la première destruction** (rebond à 1 HP) |
| 5 | **Spectre** | 40 000 | +30 % toutes stats, +10 % furtivité |

> **Grade 4 — immunité** : ton vaisseau survit miraculeusement à la première mort dans un combat (rebond à 1 HP). Reset après 48 h sans combat. Cela crée un attachement émotionnel fort à tes vétérans.
>
> **Grade 5 — Spectre** : un vaisseau Légende. Tu sentiras quand un de tes vaisseaux atteint Spectre — une animation overlay full-screen célèbre l'événement.

### XP différentielle (anti-farm)

```
XP_gagnée = base_XP × (1 + max(0, ratio_puissance - 1) × 2.5)
```

Battre un ennemi 3× plus fort que toi : **× 6** d'XP. Battre un ennemi 5× plus faible : **× 1** (plancher). Le farming des newbies n'est pas rentable, c'est voulu.

---

## 9. La Forge

Tu peux fusionner **2 vaisseaux du même type ET de la même rareté** pour obtenir un vaisseau de la **rareté supérieure** d'un cran.

- **Coût** : ×3 le coût de construction de base.
- **Durée** : 8 heures (en arrière-plan, tu peux faire autre chose).
- **Gain** : nouveau vaisseau avec les **meilleures stats** des 2 parents (max élément par élément).
- **XP transféré** : 30 % du parent le plus expérimenté.
- **Nom + trait + slots** : générés à neuf.
- Les 2 parents disparaissent (statut SCRAPPED).

> **Légendaire non forgeable** : impossible de forger 2 LEGENDARY (la rareté supérieure n'existe pas).
>
> **Soupape anti-frustration** : 2 Épiques chanceux peuvent forger un Légendaire (alors que la chance pure de tirer un Légendaire au build n'est que de 1 %).

### La Dérive (5 % de chance)

Quand le scheduler finalise ta forge, **5 % de chance** que le vaisseau sorte avec une **Dérive** :
- Une stat aléatoire parmi `hull, shield, dps, speed` réduite de **20 %**.
- Marqué `is_drift = True` (badge violet pâle, bordure pointillé dans l'UI).
- Reçoit automatiquement la cicatrice **"Né dans la Dérive"**.

Tu n'es pas chanceux ce jour-là, mais ton vaisseau a une histoire à raconter.

---

## 10. Le Pedigree

Quand tu **démolis volontairement** un vaisseau **Grade 3+**, le suivant que tu construis du **même type** peut hériter :
- **+5 %** sur la meilleure stat du parent (excluant stealth/aura).
- Mention "Issu de [nom du parent]" dans son historique.

Cela crée une **lignée générationnelle**. Conserve tes vétérans pour transmettre leur héritage.

---

## 11. Les cicatrices de combat

Un vaisseau qui survit à un combat **difficile** reçoit automatiquement une **cicatrice** narrative :
- Hull perdue ≥ **75 %** ([crawl back from death])
- OU ennemi ≥ **2× plus puissant** que toi.

Les cicatrices sont des **tags narratifs** parmi ~500 possibles : *Rescapé de la Nébuleuse Kha*, *Survivant du Siège de l'Anneau IV*, *Marqué par l'Abysse de Corvus*, *Dernier de la Flotte Brisée*…

Aucun effet mécanique. Pure narration. Mais elles sont **visibles publiquement** (n'importe quel joueur peut consulter les cicatrices de ton vaisseau via la galaxie). Fierté + intimidation.

---

## 12. Les expéditions

Lance 1 à 5 vaisseaux pour une mission autonome :

| Durée | Coût deutérium | Risque |
|---|---:|---|
| **Courte (2 h)** | 500 | Faible |
| **Moyenne (6 h)** | 1 500 | Moyen |
| **Longue (12 h)** | 4 000 | Élevé |

Au retour, ton vaisseau a vécu 1 des **12 événements** possibles :

**Bons (45 %)** : champ de débris, artefact alien, station abandonnée, cargo errant.
**Neutres (30 %)** : tempête du vide, signal étrange, erreur de navigation (perte de deutérium).
**Difficiles (20 %)** : embuscade pirate, zone radioactive, patrouille — souvent une cicatrice à la clé.
**Exceptionnels (5 %)** : épave légendaire, premier contact (modules rares, XP énorme).

Récompenses possibles : ressources (capées par capacité), XP, modules (Phase 2 : à persister), cicatrice narrative.

---

## 13. La galaxie

L'univers : **9 galaxies × 499 systèmes × 15 positions** = jusqu'à 67 365 planètes possibles.

Tu visites un système par la page **Galaxy** :
- Sélecteur galaxie 1-9 / système 1-499.
- Vue interactive des 15 slots orbitaux. Survol pour voir les détails (propriétaire, nom planète).
- Click sur une planète occupée → modal d'envoi de flotte (si pas la tienne).

### Missions de flotte

| Mission | Description |
|---|---|
| **ATTACK** | Combat les défenseurs ; pille les ressources si victoire |
| **TRANSPORT** | Apporte des ressources à une planète (homeworld, allié) |
| **ESPIONAGE** | Collecte des infos (Phase 2 — actuellement stub) |
| **COLONIZE** | Colonise une planète vide (Phase 2 — actuellement stub) |

Vitesse de flotte : minimum des speeds des vaisseaux × `FLEET_SPEED_BASE` (configurable). Distance calculée en UA selon `(galaxy_diff × 20000) + (system_diff × 5 + 1000) + (position_diff × 5 + 100)`.

Tu peux **rappeler** une flotte avant son arrivée (`DELETE /fleets/{id}`).

---

## 14. Les combats

Le serveur résout les combats automatiquement à l'arrivée d'une flotte ATTACK :

1. Calcul des puissances (DPS × hull × shield).
2. Application des **synergies** côté serveur (ATTACK+SUPPORT, DEFENSE×3+, etc.).
3. Boucle max **50 rounds**. Chaque round : tirs simultanés (cible aléatoire, DPS ±10 %).
4. Régen bouclier (Grade 3+) et hull (synergie DEFENSE+SUPPORT).
5. Calcul XP différentielle.
6. Cicatrices selon conditions.
7. **Vaisseaux détruits = perdus définitivement** (avec leur XP).

Tu reçois un **rapport WS `combat.result`** dès la résolution. Une animation **CombatReport** se déclenche en overlay : rounds animés, XP gagnée, pertes, cicatrices, synergies.

Si un de tes vaisseaux atteint Grade 5 dans le combat → animation **SpectreAwakening** dédiée.

---

## 15. Les recherches technologiques

14 technologies en 4 classes (correspondant aux 4 classes de vaisseaux) :

- **ATTACK** : weapons, speed, RNG boost…
- **DEFENSE** : armor, shields, regen…
- **SUPPORT** : aura, repair…
- **EXPLORATION** : speed, stealth, cargo, expedition_bonus…

Chaque tech a plusieurs niveaux avec coût croissant. Effets : **bonus permanents** appliqués à tous les vaisseaux de la classe correspondante. Prérequis hiérarchiques.

---

## 16. Les alliances

Tu peux **créer une alliance** si :
- Tu as **score ≥ 500** (évite les alliances fantômes).
- Tu paies **10 000 métal + 5 000 cristal**.
- Tu n'es pas déjà dans une alliance.

Une alliance a :
- **Nom** (3-32 chars, unique).
- **Tag** (2-5 chars majuscules, unique, ex. `[NOVA]`).
- **Leader** (toi le fondateur, peut être transféré).
- **Description** optionnelle (≤ 500 chars).
- **Score collectif** = somme des membres.
- **Maximum 20 membres** (pour favoriser la cohésion).

### Rôles

| Rôle | Pouvoirs |
|---|---|
| **Leader** | Tout — kick, promouvoir, déclarer guerre, dissoudre |
| **Officier** | Accepter / refuser candidatures (Phase 2) |
| **Membre** | Jouer, consulter le roster, se retirer |

### Guerres d'alliance

Un leader peut **déclarer la guerre** à une autre alliance :
- L'alliance cible reçoit une notification WS `alliance.war_declared`.
- Durée minimum : **48 h** (impossible de déclarer la paix avant).
- **Bonus XP × 1.5** sur les combats inter-alliances en guerre.
- Pour conclure : leader des deux côtés (Phase 2 — actuellement le leader d'un côté suffit).

---

## 17. Daily — récompenses quotidiennes

Connecte-toi chaque jour pour réclamer ta **récompense de connexion** :
- Cycle de 7 jours, valeurs croissantes.
- Réinitialisé à 1 si tu loupes un jour.

Tu reçois aussi **3 missions journalières** (sélection déterministe parmi 8) :
- *build_ship* : construire X vaisseaux aujourd'hui.
- *collect_metal* : collecter X métal.
- *upgrade_building* : monter un bâtiment d'un niveau.
- *send_fleet* : envoyer une flotte.
- *install_module* : installer un module.
- *check_galaxy* : visiter une nouvelle position galactique.
- *have_3_ships* : avoir au moins 3 vaisseaux.
- *forge_active* : avoir une forge active.

Chaque mission a une récompense en métal/cristal/deutérium.

---

## 18. Classement

Score = `Σ(niveaux bâtiments) × 1000 + Σ(grades vaisseaux) × 500 + Σ(combat_xp × 0.1)`.

Recalculé **toutes les 10 minutes** par le scheduler. Top 100 visible publiquement (`/ranking`). Tu vois ton rang personnel sur le Dashboard.

---

## 19. FAQ

### Le RNG est-il vraiment aléatoire ?

Oui. Le serveur utilise `secrets.SystemRandom()` (entropie de l'OS), qui est cryptographiquement non prédictible. Aucun joueur ne peut influencer ou prévoir un tirage. Aucune méthode de re-roll n'est possible : un trigger PostgreSQL empêche toute modification des `base_stats` après création.

### Pourquoi mon Légendaire est-il faible ?

Variance ±10 % à l'intérieur d'une rareté. Tu as tiré un Légendaire dans le bas de la fourchette. Astuce : forge-le avec un autre Légendaire chanceux pour cumuler les meilleures stats des deux.

### Comment je deviens Spectre (Grade 5) ?

40 000 XP de combat. Si tu gagnes 100 XP en moyenne par combat (XP_BASE = 100 pour ATTACK_WIN), il te faut 400 combats. Combats audacieux contre plus fort = beaucoup plus d'XP via XP différentielle.

### Mon vaisseau peut-il être détruit ?

Oui. Tout vaisseau avec hull à 0 est détruit définitivement (suppression de la BDD), avec son XP. Sauf un Grade 4+ avec immunité disponible (rebond à 1 HP). Choisis tes combats avec discernement.

### Combien de planètes je peux avoir ?

Pour le moment, **une seule** (la natale). La colonisation est en Phase 2.

### Je peux jouer sur mobile ?

Oui. Le frontend est mobile-first (375 px+). Toutes les pages fonctionnent sur tablette et smartphone.

### Y a-t-il un cap de stats ?

Oui. **+150 % par stat**, modules combinés. Empiler plus de modules ne sert plus à rien. L'UI marque les stats plafonnées.

### Comment je transfère le leadership d'alliance ?

Phase 2. Pour l'instant, le leader doit dissoudre ou tous les autres membres doivent partir.

### Pourquoi mes ressources stagnent ?

Cap des capacités de stockage. Ou bien ton énergie est insuffisante (`energy_factor < 1.0`). Vérifie le panneau ⚡ ÉNERGIE.

### Comment je joue avec mes amis ?

1. Ils créent un compte via le même lien.
2. Vous formez une alliance (un de vous la crée, les autres rejoignent).
3. Coordonnez vos attaques, défensives, transports.
4. Si une autre alliance vous embête : déclarez-leur la guerre (bonus XP × 1.5).

---

## 20. Astuces de stratège

1. **Diversifie tes classes.** Une flotte mono-classe est toujours faible quelque part. Essaie une combo ATTACK + SUPPORT minimum (le SUPPORT donne +20 % DPS aux ATTACK).
2. **Garde des vaisseaux Grade 3+ vivants.** Ils transmettent un Pedigree (+5 % stat) au prochain vaisseau du même type.
3. **N'attaque pas que des newbies.** XP différentielle te donne très peu. Vise des cibles équivalentes ou plus fortes.
4. **Forge tes meilleurs vaisseaux.** 2 Épiques chanceux → 1 Légendaire avec leurs meilleures stats. Compense le RNG.
5. **Surveille ton Grade 4.** Son immunité (1 HP rebound) ne se reset qu'après 48 h sans combat. Engage-le avec parcimonie.
6. **Daily login + missions tous les jours.** Le streak 7 jours donne les meilleures récompenses du cycle.
7. **Espionne avant d'attaquer (Phase 2).** En attendant, observe les alliances et leurs membres dans le classement.
8. **Construis tôt un Chantier Naval niveau 4.** Pour débloquer les croiseurs (cruiser_attack, cruiser_defense) qui sont beaucoup plus puissants que les frégates.
9. **Les expéditions longues sont plus risquées MAIS plus rentables.** Multipliers ×1.8 ressources / ×1.5 XP. À tester dès que tu as des vaisseaux solides.
10. **Rejoins une alliance dès 500 score.** Les bonus de coordination + bonus XP guerre sont énormes. Tu peux toujours quitter.

---

## 21. Glossaire

- **Base stats** : stats de base d'un vaisseau, fixées au RNG à la fabrication, **immuables**.
- **Current stats** : stats finales = base + bonus grade + bonus modules, calculées en live, plafonnées à +150 %.
- **Cap** : plafond de +150 % par stat, modules combinés.
- **Pedigree** : héritage +5 % d'une lignée Grade 3+.
- **Forge** : fusion 2 ships → 1 ship rareté supérieure (8 h, ×3 coût).
- **Dérive** : 5 % de chance lors d'une forge — stat × 0.80 + cicatrice spéciale.
- **Cicatrice** : tag narratif gagné en survivant à un combat difficile. Aucun effet mécanique.
- **Trait** : bonus narratif léger (+5-16 %) avec condition d'activation. Tiré au build.
- **XP différentielle** : XP × (1 + max(0, ratio − 1) × 2.5). Anti-farm.
- **Synergies** : bonus de combat selon la composition de la flotte (ATTACK+SUPPORT, DEFENSE×3+, etc.).
- **Immunité Grade 4** : rebond à 1 HP la première fois qu'un Grade 4 devrait mourir dans un combat. Reset 48 h.
- **Spectre** : Grade 5 — animation dédiée pour célébrer.
- **Homeworld** : ta planète natale, attribuée à l'inscription.
- **Alliance** : groupement de joueurs (max 20). Score collectif, guerres avec bonus XP.

---

*Bonne chance, capitaine. La galaxie t'attend.*
