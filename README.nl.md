<img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/custom_components/advanced_climate/brand/icon@2x.png" alt="Smart Heating Control" width="128" align="right">

# Smart Heating Control

[English](README.md) | [Română](README.ro.md) | [Deutsch](README.de.md) | **Nederlands** | [Français](README.fr.md) | [Italiano](README.it.md)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml)
[![Tests](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml)

**Blij met Smart Heating Control? Steun de ontwikkeling:**

<a href="https://ko-fi.com/sandreialexandru"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support on Ko-fi" height="44"></a>

**Verwarming voor Home Assistant die weet wie er thuis is, leert hoe elke
kamer opwarmt en vertelt waarom ze doet wat ze doet.**

Warm als je thuiskomt, koeler als er niemand is, geen warmte voor een open
raam en geen regels om te schrijven. Het werkt met wat je al hebt: Generic
Thermostat, slimme radiatorkranen, slimme thermostaten of gewoon een relais.

<p align="center"><a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-demo.gif" alt="De kaart in gebruik · verzonnen personen en gegevens" width="440"></a></p>

<p align="center"><sub>De kaart in gebruik · verzonnen personen en gegevens · <a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7">de video in betere kwaliteit</a></sub></p>

## Wat het doet

**Weet wie er thuis is.** Iedereen is *thuis*, *in de buurt* (ergens in je
stad) of *ver weg*. Het huis verwarmt voor wie er is, blijft op *eco* zolang
je alleen in de buurt bent, gaat naar *away* als iedereen ver weg is, en
verwarmt met Proximity (aanbevolen, met de richting) of een reistijdsensor
weer voor als iemand onderweg naar huis is.

**Leert elke kamer zelf kennen.** Elke kamer leert hoe snel ze opwarmt, hoe
ze afkoelt, hoe traag de radiatoren of de vloerverwarming reageren, hoe een
ketel met stooklijn meer geeft als het koud is en, met een weerentiteit,
hoeveel de zon haar verwarmt. Daarna begint ze net op tijd met verwarmen om
warm te zijn wanneer het moet, en stopt ze eerder als de kamer toch warm
genoeg blijft. Niets in te stellen: een kamer heeft ongeveer een dag nodig,
4 uur met verwarming en 4 zonder.

**Schema's die bij je week passen.** Profielen voor werkdagen, weekenden,
losse dagen of feestdagen (uit de Workday-integratie), een agenda die het
profiel van een dag kiest, of een bestaande schemahulp. Bewerk ze in de kaart
door de tijden te verslepen.

**Open ramen en handmatige wijzigingen, geregeld.** Een raamsensor of een
plotselinge temperatuurdaling zet de verwarming lager; aangrenzende kamers
kunnen meedoen. Draai je met de hand aan een thermostaat, dan blijft die
wijziging zo lang als je hebt gekozen en komt daarna het schema terug.

**Houdt rekening met het weer.** Zet de verwarming uit als het buiten warm is
(ook op basis van de voorspelling), kent een stookseizoen, verwarmt iets meer
bij strenge vorst en verlaagt een zonnige kamer.

**Energie.** Start de ketel alleen als een kamer hem nodig heeft, volgt een
dynamisch tarief of zonnestroomoverschot en telt de verwarmingstijd per dag,
week of maand.

**Veilig.** Altijd vorstbeveiliging, een maximumtemperatuur, elke opdracht
gecontroleerd en opnieuw verstuurd als die niet aankwam, meldingen bij open
ramen, onbeschikbare apparaten, lege batterijen en **schimmelrisico** bij de
koudste muur, en wekelijks doorbewegen van de radiatorkranen.

**Legt zichzelf uit.** Elke kamer heeft een sensor *Beslissing* met de regel
die won en de reden, een event bij elke wijziging en diagnostiek met de
laatste 100 beslissingen.

**Past bij je huis.** Generic Thermostat (alleen de preset wordt gekozen; je
thermostaat werkt zoals altijd), radiatorkranen met kalibratie via een
kamersensor, andere thermostaten, relais. °C of °F per huis. In het
Nederlands, Engels, Roemeens, Duits, Frans en Italiaans.

## De kaart

Er hoort een Lovelace-kaart bij de integratie, die vanzelf aan de bronnen van
het dashboard wordt toegevoegd.

<table>
  <tr>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-hero.png" alt="Het huis met de personen, de modus en de knoppen, een open kamer en de andere ingeklapt" width="360"><br><sub>Het huis en zijn kamers</sub></td>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-details.png" alt="Details van een kamer: temperaturen, vochtigheid, de volgende optimale stop en wat de kamer heeft geleerd" width="360"><br><sub>Wat een kamer heeft geleerd</sub></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-chart.png" alt="De grafiek: temperatuur, doel, verwarmen, buitentemperatuur en de voorspelde temperatuur" width="720"><br><sub>7 dagen geschiedenis en de komende 12 uur, met de temperatuur die de kamer verwacht</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-light.png" alt="Een handmatige wijziging met het deel Tijdelijk instellen open, licht thema" width="360"><br><sub>Tijdelijk een niveau of temperatuur instellen</sub></td>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-compact.png" alt="Compacte kaart: één tegel per kamer" width="360"><br><sub>Compact: één tegel per kamer</sub></td>
  </tr>
</table>

```yaml
type: custom:smart-heating-control-card
```

Elk onderdeel kan verborgen worden; de opties staan in de
[handleiding](docs/guide/10-card.md) (Engels).

## Aan de slag

[![Open je Home Assistant en voeg deze repository toe](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sandreialexandru&repository=Smart-Heating-Control&category=integration)

1. **Installeer** via HACS (vanaf Home Assistant 2026.11 de **Marketplace**):
   zoek op **Smart Heating Control**, installeer het en herstart Home
   Assistant. Niet gevonden? Open het met de knop hierboven, of voeg het met
   de hand toe: ⋮ → **Aangepaste repositories** →
   `https://github.com/sandreialexandru/Smart-Heating-Control` als
   **Integratie**. Zonder HACS kopieer je `custom_components/advanced_climate`
   naar `config/custom_components`.
2. **Maak het huis aan**: **Instellingen → Apparaten en diensten → Integratie
   toevoegen → Smart Heating Control**, of met deze knop:

   [![Open je Home Assistant en voeg Smart Heating Control toe](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=advanced_climate)

   Kies de personen en de thermostaat die het huis verwarmt, en voor een huis
   met één thermostaat ben je klaar.
3. **Voeg kamers toe** (optioneel) met hun eigen kranen of thermostaten, op
   de pagina van de integratie, en zet de kaart op een dashboard.

Vereist Home Assistant **2026.6.0** of nieuwer.

**Twijfel je wat je moet kiezen?** De
[interactieve configurator](https://github.com/sandreialexandru/Smart-Heating-Control/blob/main/docs/configurator.html)
(Engels of Roemeens) begint met wat je huis verwarmt en vult de bijpassende
antwoorden in, loopt elk formulier door, legt elke keuze uit met wat ze
verandert en een voorbeeld, en eindigt met een overzicht van wat je instelt
en de problemen die hij vond (zoals één apparaat in twee rollen). Download het
bestand en open het in een browser.

## Documentatie

De documentatie is in het Engels en Roemeens.

| Document | Wat erin staat |
|---|---|
| [Handleiding](docs/guide/README.md) | Stap voor stap, in gewone taal: elke instelling, elk soort verwarming, voorbeelden |
| [Getest met](docs/tested-with.md) | De apparaten die gebruikers hebben bevestigd |
| [Hoe de integratie leert](docs/learning.md) | Het kamermodel, met uitgewerkte voorbeelden en simulaties |
| [Referentie](docs/reference.md) | Elke regel, sensor, attribuut, dienst en kaartoptie, technisch in detail |
| [Specificatie](docs/SPEC.md) | De volledige specificatie |
| [Wijzigingen](CHANGELOG.md) | Wat er veranderd is, versie voor versie |

## Vertalingen

Integratie en kaart: Engels, Roemeens, Duits, Nederlands, Frans en
Italiaans. Documentatie: Engels en Roemeens.

De Nederlandse teksten zijn nieuw. Klinkt iets vreemd of zou jij het anders
zeggen? Help mee in [dit issue](https://github.com/sandreialexandru/Smart-Heating-Control/issues/12).

## Steun

Heb je iets aan Smart Heating Control? Trakteer me op een koffie via
[Ko-fi](https://ko-fi.com/sandreialexandru). Bedankt!

## Licentie

MIT
