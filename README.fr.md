<img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/custom_components/advanced_climate/brand/icon@2x.png" alt="Smart Heating Control" width="128" align="right">

# Smart Heating Control

[English](README.md) | [Română](README.ro.md) | [Deutsch](README.de.md) | [Nederlands](README.nl.md) | **Français** | [Italiano](README.it.md)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml)
[![Tests](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml)

**Smart Heating Control vous plaît ? Soutenez son développement :**

<a href="https://ko-fi.com/sandreialexandru"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support on Ko-fi" height="44"></a>

**Un chauffage pour Home Assistant qui sait qui est à la maison, apprend
comment chaque pièce se réchauffe et vous dit pourquoi il fait ce qu'il fait.**

Au chaud quand vous rentrez, plus frais quand il n'y a personne, pas de
chaleur perdue par une fenêtre ouverte et aucune règle à écrire. Il fonctionne
avec ce que vous avez déjà : Generic Thermostat, têtes thermostatiques,
thermostats connectés ou un simple relais.

<p align="center"><a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-demo.gif" alt="La carte en action · personnes et données inventées" width="440"></a></p>

<p align="center"><sub>La carte en action · personnes et données inventées · <a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7">la vidéo en meilleure qualité</a></sub></p>

## Ce qu'il fait

**Sait qui est à la maison.** Chaque personne est *à la maison*, *à
proximité* (quelque part dans votre ville) ou *loin*. La maison chauffe pour
ceux qui sont là, reste en *eco* tant que vous êtes seulement à proximité,
passe en *away* quand tout le monde est loin et, avec Proximity (recommandé,
avec sa direction) ou un capteur de temps de trajet, se remet à chauffer quand
quelqu'un rentre.

**Apprend chaque pièce tout seul.** Chaque pièce apprend à quelle vitesse elle
se réchauffe, comment elle refroidit, avec quelle lenteur réagissent ses
radiateurs ou son plancher chauffant, comment une chaudière avec courbe de
chauffe donne plus quand il fait froid et, avec une entité météo, combien le
soleil la réchauffe. Elle commence alors à chauffer juste assez tôt pour être
chaude à l'heure, et s'arrête plus tôt quand elle restera de toute façon
confortable. Rien à régler : une pièce a besoin d'environ une journée, 4
heures avec chauffage et 4 sans.

**Des plannings qui suivent votre semaine.** Des profils pour les jours
ouvrés, le week-end, des jours précis ou les jours fériés (avec l'intégration
Workday), un calendrier qui choisit le profil d'une journée, ou une entrée
Programmation existante. Modifiez-les dans la carte en faisant glisser les
heures.

**Fenêtres ouvertes et modifications manuelles, gérées.** Un capteur de
fenêtre ou une chute brutale de température baisse le chauffage ; les pièces
voisines peuvent suivre. Tournez un thermostat à la main et la modification
est gardée aussi longtemps que vous l'avez choisi, puis le planning reprend.

**Attentif à la météo.** Coupe le chauffage quand il fait doux dehors (aussi
d'après les prévisions), gère une saison de chauffe, ajoute un peu de chaleur
par grand froid et baisse une pièce ensoleillée.

**Énergie.** Ne démarre la chaudière que lorsqu'une pièce en a besoin, suit
un tarif dynamique ou un surplus solaire, passe sur une deuxième source de
chaleur (la pompe à chaleur tant qu'il y a du soleil, la chaudière par grand
froid) et compte le temps de chauffe par jour, semaine ou mois.

**Sûr.** Toujours le hors-gel, une température maximale, chaque commande
vérifiée et renvoyée si elle n'est pas arrivée, des alertes pour les fenêtres
ouvertes, les appareils indisponibles, les piles faibles et le **risque de
moisissure** sur le mur le plus froid, et un dégommage hebdomadaire des
têtes thermostatiques.

**S'explique tout seul.** Chaque pièce a un capteur *Décision* avec la règle
qui l'a emporté et la raison, un événement à chaque changement et des
diagnostics avec les 100 dernières décisions.

**S'adapte à votre maison.** Generic Thermostat (seul le préréglage est
choisi ; votre thermostat fonctionne comme avant), têtes thermostatiques
calibrées par un capteur de pièce, autres thermostats, relais. °C ou °F par
maison. En français, anglais, roumain, allemand, néerlandais et italien.

## La carte

Une carte Lovelace est fournie avec l'intégration et s'ajoute toute seule aux
ressources du tableau de bord.

<table>
  <tr>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-hero.png" alt="La maison avec ses personnes, son mode et ses boutons, une pièce ouverte et les autres repliées" width="360"><br><sub>La maison et ses pièces</sub></td>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-details.png" alt="Détails d'une pièce : températures, humidité, le prochain arrêt optimal et ce que la pièce a appris" width="360"><br><sub>Ce qu'une pièce a appris</sub></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-chart.png" alt="Le graphique : température, consigne, chauffe, température extérieure et température prévue" width="720"><br><sub>7 jours d'historique et les 12 prochaines heures, avec la température que la pièce attend</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-light.png" alt="Une modification manuelle avec la partie Régler pour un moment ouverte, thème clair" width="360"><br><sub>Régler un niveau ou une température pour un moment</sub></td>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-compact.png" alt="Carte compacte : une tuile par pièce" width="360"><br><sub>Compacte : une tuile par pièce</sub></td>
  </tr>
</table>

```yaml
type: custom:smart-heating-control-card
```

Chaque partie peut être masquée ; les options sont dans le
[guide](docs/guide/10-card.md) (en anglais).

## Démarrer

[![Ouvrez votre Home Assistant et ajoutez ce dépôt](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sandreialexandru&repository=Smart-Heating-Control&category=integration)

1. **Installez** depuis HACS (le **Marketplace** à partir de Home Assistant
   2026.11) : cherchez **Smart Heating Control**, installez-le et redémarrez
   Home Assistant. Introuvable dans la recherche ? Ouvrez-le avec le bouton
   ci-dessus, ou ajoutez-le à la main : ⋮ → **Dépôts personnalisés** →
   `https://github.com/sandreialexandru/Smart-Heating-Control` comme
   **Intégration**. Sans HACS, copiez `custom_components/advanced_climate`
   dans `config/custom_components`.
2. **Ajoutez la maison** : **Paramètres → Appareils et services → Ajouter une
   intégration → Smart Heating Control**, ou avec ce bouton :

   [![Ouvrez votre Home Assistant et ajoutez Smart Heating Control](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=advanced_climate)

   Choisissez les personnes et le thermostat qui chauffe la maison : pour une
   maison avec un seul thermostat, c'est terminé.
3. **Ajoutez des pièces** (facultatif) avec leurs propres vannes ou
   thermostats, depuis la page de l'intégration, et placez la carte sur un
   tableau de bord.

Nécessite Home Assistant **2026.6.0** ou plus récent.

**Vous hésitez ?** Le
[configurateur interactif](https://github.com/sandreialexandru/Smart-Heating-Control/blob/main/docs/configurator.html)
(en anglais ou en roumain) part de ce qui chauffe votre logement et remplit les
réponses qui vont avec, parcourt chaque formulaire, explique chaque choix avec
ce qu'il change et un exemple, et se termine par un résumé de ce qu'il faut
régler et des problèmes trouvés (comme un appareil dans deux rôles).
Téléchargez le fichier et ouvrez-le dans un navigateur.

## Documentation

La documentation est en anglais et en roumain.

| Document | Contenu |
|---|---|
| [Guide](docs/guide/README.md) | Pas à pas, avec des mots simples : chaque réglage, chaque type de chauffage, des exemples |
| [Testé avec](docs/tested-with.md) | Les appareils confirmés par les utilisateurs |
| [Comment l'intégration apprend](docs/learning.md) | Le modèle de la pièce, avec des exemples chiffrés et des simulations |
| [Référence](docs/reference.md) | Chaque règle, capteur, attribut, service et option de la carte, en détail technique |
| [Spécification](docs/SPEC.md) | La spécification complète |
| [Changements](CHANGELOG.md) | Ce qui a changé, version par version |

## Traductions

Intégration et carte : anglais, roumain, allemand, néerlandais, français et
italien. Documentation : anglais et roumain.

Les textes en français sont nouveaux. Quelque chose sonne bizarre ou vous le
diriez autrement ? Aidez-nous dans [ce ticket](https://github.com/sandreialexandru/Smart-Heating-Control/issues/12).

## Soutien

Si Smart Heating Control vous est utile, vous pouvez m'offrir un café sur
[Ko-fi](https://ko-fi.com/sandreialexandru). Merci !

## Licence

MIT
