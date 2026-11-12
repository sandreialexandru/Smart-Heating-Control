<img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/custom_components/advanced_climate/brand/icon@2x.png" alt="Smart Heating Control" width="128" align="right">

# Smart Heating Control

[English](README.md) | [Română](README.ro.md) | **Deutsch** | [Nederlands](README.nl.md) | [Français](README.fr.md) | [Italiano](README.it.md)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml)
[![Tests](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml)

**Gefällt dir Smart Heating Control? Unterstütze die Entwicklung:**

<a href="https://ko-fi.com/sandreialexandru"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support on Ko-fi" height="44"></a>

**Eine Heizungssteuerung für Home Assistant, die weiß, wer zu Hause ist,
lernt, wie jeder Raum warm wird, und dir sagt, warum sie tut, was sie tut.**

Warm, wenn du heimkommst, kühler, wenn niemand da ist, keine Wärme fürs
offene Fenster und keine Regeln zum Schreiben. Sie arbeitet mit dem, was du
schon hast: Generic Thermostat, Heizkörperthermostate, smarte Thermostate
oder ein einfaches Relais.

<p align="center"><a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-demo.gif" alt="Die Karte im Einsatz · erfundene Personen und Daten" width="440"></a></p>

<p align="center"><sub>Die Karte im Einsatz · erfundene Personen und Daten · <a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7">das Video in besserer Qualität</a></sub></p>

## Was sie macht

**Weiß, wer zu Hause ist.** Jede Person ist *zu Hause*, *in der Nähe*
(irgendwo in deiner Stadt) oder *weit weg*. Das Haus heizt für alle, die da
sind, bleibt auf *Eco*, solange ihr nur in der Nähe seid, geht auf *Away*,
wenn alle weit weg sind, und heizt mit Proximity (empfohlen, mit Richtung)
oder einem Fahrzeitsensor wieder vor, wenn jemand auf dem Heimweg ist.

**Lernt jeden Raum von selbst.** Jeder Raum lernt, wie schnell er warm wird,
wie er abkühlt, wie träge seine Heizkörper oder seine Fußbodenheizung
reagieren, wie ein Kessel mit Heizkurve bei Kälte mehr liefert und, mit einer
Wetter-Entität, wie stark die Sonne ihn wärmt. Dann beginnt er gerade so früh
zu heizen, dass es pünktlich warm ist, und hört früher auf, wenn der Raum
ohnehin warm genug bleibt. Nichts einzustellen: Ein Raum braucht etwa einen
Tag, 4 Stunden mit Heizen und 4 ohne.

**Zeitpläne, die zu deiner Woche passen.** Profile für Arbeitstage,
Wochenenden, einzelne Tage oder Feiertage (aus der Workday-Integration), ein
Kalender, der das Profil eines Tages wählt, oder ein vorhandener
Zeitplan-Helfer. Bearbeitet werden sie in der Karte, indem du die Uhrzeiten
ziehst.

**Offene Fenster und manuelle Änderungen im Griff.** Ein Fenstersensor oder
ein plötzlicher Temperaturabfall senkt die Heizung; Nachbarräume können
folgen. Drehst du von Hand am Thermostat, gilt die Änderung so lange, wie du
es eingestellt hast, dann kommt der Zeitplan zurück.

**Kennt das Wetter.** Schaltet die Heizung ab, wenn es draußen warm ist (auch
nach der Vorhersage), kennt eine Heizperiode, legt bei starkem Frost etwas
drauf und senkt einen sonnigen Raum ab.

**Energie.** Startet den Kessel nur, wenn ein Raum ihn braucht, folgt einem
dynamischen Tarif oder PV-Überschuss und zählt die Heizzeit pro Tag, Woche
oder Monat.

**Sicher.** Immer Frostschutz, eine Höchsttemperatur, jeder Befehl wird
geprüft und erneut gesendet, wenn er nicht ankam, Warnungen bei offenen
Fenstern, nicht verfügbaren Geräten, schwachen Batterien und **Schimmelgefahr**
an der kältesten Wand, und eine wöchentliche Ventilbewegung für
Heizkörperthermostate.

**Erklärt sich selbst.** Jeder Raum hat einen Sensor *Entscheidung* mit der
Regel, die gewonnen hat, und dem Grund, ein Ereignis bei jeder Änderung und
Diagnosedaten mit den letzten 100 Entscheidungen.

**Passt zu deinem Haus.** Generic Thermostat (es wird nur das Preset gewählt;
dein Thermostat arbeitet weiter wie bisher), Heizkörperthermostate mit
Kalibrierung über einen Raumsensor, andere Thermostate, Relais. °C oder °F
pro Haus. Auf Deutsch, Englisch, Rumänisch, Niederländisch, Französisch und
Italienisch.

## Die Karte

Eine Lovelace-Karte gehört zur Integration und wird von selbst zu den
Ressourcen des Dashboards hinzugefügt.

<table>
  <tr>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-hero.png" alt="Das Haus mit Personen, Modus und Schaltflächen, ein offener Raum und die anderen eingeklappt" width="360"><br><sub>Das Haus und seine Räume</sub></td>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-details.png" alt="Details eines Raums: Temperaturen, Feuchtigkeit, der nächste optimale Stopp und was der Raum gelernt hat" width="360"><br><sub>Was ein Raum gelernt hat</sub></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-chart.png" alt="Das Diagramm: Temperatur, Ziel, Heizen, Außentemperatur und die vorhergesagte Temperatur" width="720"><br><sub>7 Tage Verlauf und die nächsten 12 Stunden, mit der Temperatur, die der Raum erwartet</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-light.png" alt="Eine manuelle Änderung mit geöffnetem Bereich Für eine Weile setzen, helles Design" width="360"><br><sub>Eine Stufe oder Temperatur für eine Weile setzen</sub></td>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-compact.png" alt="Kompakte Karte: eine Kachel pro Raum" width="360"><br><sub>Kompakt: eine Kachel pro Raum</sub></td>
  </tr>
</table>

```yaml
type: custom:smart-heating-control-card
```

Jeder Teil lässt sich ausblenden; die Optionen stehen in der
[Anleitung](docs/guide/10-card.md) (Englisch).

## Loslegen

[![Öffne dein Home Assistant und füge dieses Repository hinzu](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sandreialexandru&repository=Smart-Heating-Control&category=integration)

1. **Installieren** über HACS (ab Home Assistant 2026.11 der **Marketplace**):
   Suche nach **Smart Heating Control**, installiere es und starte Home
   Assistant neu. Nicht in der Suche? Öffne es mit der Schaltfläche oben oder
   füge es von Hand hinzu: ⋮ → **Benutzerdefinierte Repositories** →
   `https://github.com/sandreialexandru/Smart-Heating-Control` als
   **Integration**. Ohne HACS kopierst du `custom_components/advanced_climate`
   nach `config/custom_components`.
2. **Das Haus anlegen**: **Einstellungen → Geräte & Dienste → Integration
   hinzufügen → Smart Heating Control**, oder diese Schaltfläche:

   [![Öffne dein Home Assistant und füge Smart Heating Control hinzu](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=advanced_climate)

   Wähle die Personen und das Thermostat, das das Haus heizt – bei einem Haus
   mit einem Thermostat bist du damit fertig.
3. **Räume hinzufügen** (optional) mit eigenen Ventilen oder Thermostaten,
   auf der Seite der Integration, und die Karte auf ein Dashboard setzen.

Braucht Home Assistant **2026.6.0** oder neuer.

**Unsicher, was du wählen sollst?** Der
[interaktive Konfigurator](https://github.com/sandreialexandru/Smart-Heating-Control/blob/main/docs/configurator.html)
(Englisch oder Rumänisch) beginnt mit dem, was dein Zuhause heizt, füllt die
passenden Antworten aus, führt durch jedes Formular, erklärt jede Wahl mit
ihrer Wirkung und einem Beispiel und endet mit einer Übersicht, was einzustellen
ist, und den gefundenen Problemen (etwa ein Gerät in zwei Rollen). Lade die
Datei herunter und öffne sie im Browser.

## Dokumentation

Die Dokumentation gibt es auf Englisch und Rumänisch.

| Dokument | Inhalt |
|---|---|
| [Anleitung](docs/guide/README.md) | Schritt für Schritt, in einfachen Worten: jede Einstellung, jede Art von Heizung, Beispiele |
| [Getestet mit](docs/tested-with.md) | Die Geräte, die Nutzer bestätigt haben |
| [Wie die Integration lernt](docs/learning.md) | Das Raummodell, mit durchgerechneten Beispielen und Simulationen |
| [Referenz](docs/reference.md) | Jede Regel, jeder Sensor, jedes Attribut, jeder Dienst und jede Kartenoption, technisch im Detail |
| [Spezifikation](docs/SPEC.md) | Die vollständige Spezifikation |
| [Änderungen](CHANGELOG.md) | Was sich geändert hat, Version für Version |

## Übersetzungen

Integration und Karte: Englisch, Rumänisch, Deutsch, Niederländisch,
Französisch und Italienisch. Dokumentation: Englisch und Rumänisch.

Die deutschen Texte sind neu. Klingt etwas seltsam oder nicht so, wie du es
sagen würdest? Hilf mit in [diesem Issue](https://github.com/sandreialexandru/Smart-Heating-Control/issues/12).

## Unterstützung

Wenn dir Smart Heating Control nützt, kannst du mir auf
[Ko-fi](https://ko-fi.com/sandreialexandru) einen Kaffee spendieren. Danke!

## Lizenz

MIT
