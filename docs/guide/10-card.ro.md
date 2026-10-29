# 10. Cardul

*[English](10-card.md) · [Cuprins](README.ro.md)*

Integrarea are un card Lovelace cu toate comenzile: casa, camerele, graficul,
programul editabil și detaliile.

## Adăugarea cardului

Integrarea adaugă singură cardul la resursele dashboard-urilor (adresa
`/advanced_climate/smart-heating-control-card.js?v=<versiune>`, schimbată la
fiecare versiune, ca browserul și aplicația să încarce versiunea nouă). Cu
dashboard-uri în mod YAML adaugi singur adresa ca resursă de tip `module`.

În dashboard: **Adaugă card → Smart Heating Control**. Are editor vizual. Fără
nicio opțiune arată toate casele și camerele:

```yaml
type: custom:smart-heating-control-card
```

## Opțiunile cardului

| Opțiune | Implicit | Ce face |
| --- | --- | --- |
| `title` | Încălzire | Titlul cardului (un text gol îl ascunde). |
| `rooms` | toate | Lista senzorilor *Decizie* ai camerelor de arătat. |
| `show_house` | `true` | Partea casei (vezi mai jos). |
| `show_rooms` | `true` | Camerele. |
| `show_timeline` | `true` | Graficul fiecărei camere. |
| `show_quick_override` | `true` | *Setează temporar*. |
| `show_levels` | `true` | Temperaturile nivelurilor. |
| `show_details` | `true` | *Detaliile* camerei. |
| `show_schedule_editor` | `true` | Editorul programului. |
| `collapsed` | `false` | Camerele încep pliate (un rând: un arc mic, numele cu decizia, timpul până la țintă, nivelul și ținta); atingi rândul ca să deschizi camera. |
| `compact` | `false` | O placă pe cameră (numele cu decizia, arc cu temperatura, nivel, țintă, o iconiță de stare) și un rând pentru casă; atingi ca să deschizi. |
| `runtime_period` | `day` | Timpul de încălzire pe `day`, `week` sau `month` (perioade calendaristice, din statisticile pe termen lung); se schimbă și atingând valoarea în card. |

**Exemplu**: un card doar pentru dormitor, pliat, fără editorul de program:

```yaml
type: custom:smart-heating-control-card
title: Dormitor
show_house: false
rooms:
  - sensor.dormitor_decision
show_schedule_editor: false
collapsed: true
```

## Partea casei

- **Prezența**, cu fiecare persoană ca un cerc (poza sau inițiala) în culoarea
  locului unde e: portocaliu acasă, verde aproape, gri departe.
- Plăci pentru **media temperaturii de afară** (pe orele din *Medie pe*),
  **sezon**, **cererea de căldură** și **timpul de încălzire**.
- **Modul** (Auto / Vacanță / Oprit / Vară).
- Un rând de butoane: **Pauză** și **Oaspeți** (pornit / oprit), **Vacanță**
  (deschide datele vacanței), **Reevaluează** și **Automat** (anulează toate
  modificările manuale). Un buton rămâne colorat cât modul lui e pornit.
- **Cald afară**, cât încălzirea e oprită pentru că e cald, cu motivul (media
  măsurată sau prognoza) sau când prognoza lasă încălzirea să pornească (vezi
  [capitolul 6](06-vreme.ro.md)). Nu apare unde nu are efect: modul Oprit sau
  Vară, în afara sezonului, în pauză.
- O **bandă de pauză** sus cât casa e în pauză și o **bandă de oaspeți** cât
  modul oaspeți e pornit (cu sfârșitul lui, când are unul).
- În cardul compact, rândul pliat al casei arată persoanele, modul,
  temperatura de afară și o flacără cât există cerere de căldură.

## O cameră

Antetul arată numele, decizia (de exemplu *Aproape*, *Program*; în culoarea
nivelului) și insignele pentru încălzire (pulsează), fereastră deschisă și
modificare manuală. Decizia rămâne lângă nume în orice vedere (cameră deschisă,
rând pliat, placă compactă); **nivelul** (de exemplu *eco*) apare separat: sub
arc în camera deschisă, lângă țintă în rândul pliat, în placă. Sub antet:

- un **arc** cu temperatura camerei și ținta sub ea; arcul e gol la antiîngheț
  și plin la temperatura maximă a camerei (doar arată temperatura, nu schimbă
  nimic);
- lângă el **motivul** (în limba cardului), **timpul până la țintă** (de exemplu
  *~35 min*) sau, în timpul unei opriri anticipate, **temperatura estimată la
  schimbare** (*~21.5° la 22:00*), **forțarea TRV** când e pornită pentru
  cameră și ce măsoară dispozitivul însuși (camerele cu TRV / dispozitive
  climate);
- **Azi**: profilul zilei ca bară de la 00 la 24, cu ora de acum.
Dacă o cameră sub țintă nu încălzește, cardul spune de ce (*Nu încălzește: …*,
vezi [capitolul 8](08-sursa-si-energie.ro.md#când-nu-încălzește-o-cameră-sub-țintă)).
Butonul *Înapoi la automat* anulează o modificare manuală.

Sub grafic, butoanele deschid secțiunile **Setează temporar**, **Program**,
**Niveluri** și **Detalii**, fiecare separat (pot fi deschise mai multe deodată);
butonul unei secțiuni deschise rămâne colorat. Graficul și secțiunile:

### Graficul

Ultimele 24 de ore și următoarele 12:

- temperatura camerei;
- ținta, ca linie în trepte, colorată după nivel;
- nivelurile planificate;
- perioadele în care camera a încălzit, pe o bandă separată;
- temperatura de afară pe banda ei (măsurată, apoi prognoza orară punctat) și
  pragul de oprire ca linie punctată;
- următoarea pornire / oprire anticipată, ca perioadă umbrită.

Valorile se citesc cu mouse-ul, la atingere sau trăgând pe grafic. Zoom cu
butoanele (1h, 6h, −, +), dublu clic, ciupire sau Ctrl + rotiță, până la 20 de
minute; când e mărit, te muți în timp trăgând fereastra din bara de sub grafic.

Partea planificată arată ce se va întâmpla: programul; o modificare manuală cu
durată până la sfârșitul ei; o vacanță planificată până la preîncălzire; un
eveniment din calendar până la sfârșitul lui. O fereastră, antiînghețul sau
mișcarea robinetelor apar doar pentru acum. Modul Oprit / Vară, pauza, plecarea,
senzorii căzuți și *Cald afară* apar așa cum sunt acum, pe toată perioada.

### Setează temporar

Pui un nivel sau o temperatură pentru un număr de ore: *[Setează] [21] °C pentru
[2] h*. Ore goale = regula configurată pentru modificările manuale. Tot aici e
comutatorul **Blocare modificări**.

### Niveluri

Temperaturile nivelurilor (camerele fără Generic Thermostat) și temperatura
fixă pentru *aproape*. Se schimbă direct din card, între antiîngheț și maxim.

### Program

Fiecare profil cu zilele lui și un comutator pornit / oprit:

- **orele de început** se trag pe bara zilei, în pași de 5 minute;
- **zilele** se aleg în editor (toate, lucrătoare, weekend, zile anume);
- un profil se poate **copia** peste altul;
- cardul te avertizează înainte ca pornirea sau oprirea unui profil să lase
  zile fără profil (care ar rămâne pe antiîngheț).

### Detalii

Pe grupuri:

- **alertele** camerei și ale casei, primele;
- **Temperaturi**: camera, ținta, presetul termostatului, ajustările active,
  temperaturile nivelurilor;
- **Program**: următoarea pornire / oprire anticipată, timpul de încălzire;
- **Învățare**: încălzirea (episoade, partea fixă și minutele pe grad acum) și
  răcirea (episoade și cât de repede scade camera acum), fiecare cu butonul
  **Resetează** (cu un al doilea clic pentru confirmare), apoi ultimul episod de
  încălzire.

La o modificare manuală, cardul arată unde a fost făcută (card / serviciu sau pe
dispozitiv), până când, *se aplică după: …* sau *revine după: …*.

Aproape orice valoare, stare sau insignă deschide la atingere fereastra cu
detaliile entității.

## Limba

Cardul e în engleză și română, după limba Home Assistant. Motivul deciziei și
numele ajustărilor sunt traduse (senzorul *Decizie* le are ca `reason_key` și
`reason_params`; `reason` rămâne textul în engleză).
