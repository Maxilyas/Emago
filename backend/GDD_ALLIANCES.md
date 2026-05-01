# GDD — Système d'Alliances Emago v1.0
# Agent 2 — Game Designer | Sprint 4

## Vue d'ensemble

Les alliances sont des groupements de joueurs (max 20 membres) qui partagent
un score collectif et peuvent déclarer des guerres entre elles.
Elles ne donnent pas d'avantage pay-to-win : seule la coordination compte.

---

## Mécanique de création

Un joueur peut créer une alliance si :
- Il n'est pas déjà dans une alliance
- Il a un score ≥ 500 (évite la création d'alliances fantômes par les nouveaux)
- Il paie le coût de création : 10 000 métal + 5 000 cristal

Une alliance a :
- Un **nom** (3-32 caractères, unique, alphanumérique + espaces)
- Un **tag** (2-5 caractères majuscules, unique)  ex: [NOVA]
- Un **leader** (le fondateur — peut être transféré)
- Une **description** optionnelle (500 caractères max)
- Un **score collectif** = somme des scores des membres

## Rôles

| Rôle | Pouvoir |
|---|---|
| Leader | Tout (kick, promouvoir, diplomatie, dissoudre) |
| Officier | Accepter/refuser candidatures, gérer ambassades |
| Membre | Jouer, consulter le roster, se retirer |

## Candidatures

- Un joueur peut postuler à une alliance ouverte
- Le leader/officier accepte ou refuse
- Si accepté, il rejoint avec le rôle Membre
- Délai de re-candidature : 24h après un refus ou une expulsion

## Limite de membres
- Maximum 20 membres par alliance
- GDD décision : petite taille pour encourager la cohésion

---

## Diplomatie

| Relation | Effet |
|---|---|
| Neutre (défaut) | Aucun |
| Pacte de non-agression (PNA) | Attaque entre membres des deux alliances impossible |
| Guerre déclarée | Bonus XP ×1.5 pour les combats entre membres des deux alliances |

### Guerre déclarée
- Déclarée unilatéralement par le leader d'une alliance
- L'alliance cible reçoit une notification WS `alliance.war_declared`
- Durée minimum : 48h (on ne peut pas déclarer la paix avant)
- Fin : les deux leaders déclarent la paix, ou l'une des alliances est dissoute

---

## Score collectif

`alliance.score = SUM(membre.score for membre in membres)`

Recalculé toutes les 10 minutes par le scheduler ranking (déjà existant).

---

## Dissolution

- Le leader peut dissoudre si l'alliance a ≤ 1 membre (lui seul)
- Ou si tous les membres ont quitté
- Une alliance dissoute libère le tag et le nom

---

## Formules / Valeurs

| Paramètre | Valeur |
|---|---|
| Membres max | 20 |
| Score minimum pour créer | 500 |
| Coût de création | 10 000 métal + 5 000 cristal |
| Tag longueur | 2-5 caractères |
| Durée minimum guerre | 48h |
| XP bonus guerre | ×1.5 sur les combats inter-alliance |

---

## Notes pour les développeurs (Agent 5, 6, 7)

- La table `alliances` existe déjà — ajouter `alliance_members` et `alliance_wars`
- Le champ `player.alliance_id` existe — le mettre à jour à l'entrée/sortie
- L'endpoint GET /ranking renvoie déjà `alliance_tag: null` — le brancher
- Les events WS `alliance.war_declared` et `alliance.peace` sont nouveaux
- Le bonus XP ×1.5 guerre est ajouté dans `combat_engine.py`

---

## Cas limites à gérer

- Un leader qui quitte doit transférer le leadership ou dissoudre
- Un membre expulsé en combat actif : le combat continue normalement
- Une dissolution d'alliance en guerre : la guerre prend fin automatiquement
- Si alliance_id du player est NULL mais alliance_members a une entrée → incohérence à logger
