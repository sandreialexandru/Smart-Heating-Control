# 10. Cardul

*[English](10-card.md) · [Cuprins](README.ro.md)*

Integrarea are un card Lovelace cu toate comenzile: casa, camerele, graficul,
programul editabil și detaliile.

<p align="center"><img src="../images/card-demo.gif" alt="Cardul în folosire" width="400"><br><sub>▶️ <a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7">Tot videoclipul (30 s, MP4)</a> · date inventate</sub></p>

## Adăugarea cardului

Integrarea adaugă singură cardul la resursele dashboard-urilor (adresa
`/advanced_climate/smart-heating-control-card.js?v=<versiune>`, schimbată la
fiecare versiune, ca browserul și aplicația să încarce versiunea nouă). Cu
dashboard-uri în mod YAML adresa se adaugă manual ca resursă de tip `module`.

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
| `show_house` | `true` | Partea casei (mai jos). |
| `show_rooms` | `true` | Camerele. |
| `show_timeline` | `true` | Butonul **Grafic** al fiecărei camere (graficul se deschide cu el). |
| `show_quick_override` | `true` | *Setează temporar*. |
| `show_levels` | `true` | Temperaturile nivelurilor. |
| `show_details` | `true` | *Detaliile* camerei. |
| `show_schedule_editor` | `true` | Editorul programului. |
| `collapsed` | `false` | Camerele încep pliate (un rând: un arc mic, numele, timpul până la țintă, iconițele de stare, nivelul și ținta); camera se deschide atingând rândul. |
| `compact` | `false` | O placă pe cameră (numele, iconițele de stare, arc cu temperatura, nivel, țintă) și un rând pentru casă; se deschide la atingere. |
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

<p align="center"><img src="../images/card-compact.png" alt="Cardul compact: o placă pe cameră" width="380"></p>

## Partea casei

<p align="center"><img src="../images/card-hero.png" alt="Casa cu persoanele, modul și butoanele, o cameră deschisă și celelalte pliate" width="380"></p>

- **Flacăra** lângă prezență (mai jos) cât casa cere căldură; pâlpâie cât
  o cameră a casei chiar încălzește.
- **Titlul** e același în orice vedere: iconița și numele casei, prezența
  (Acasă / Aproape / Departe) și flacăra.
- **Prezența**, cu fiecare persoană ca un cerc (poza sau inițiala) în culoarea
  locului unde e: portocaliu acasă, verde aproape, gri departe.
- Plăci pentru **media temperaturii de afară** (pe orele din *Medie pe*),
  **sezon**, **cererea de căldură** și **timpul de încălzire**: două câte două
  pe un card îngust (trei pe rând fără timpul de încălzire), toate pe un rând
  pe unul lat.
- **Modul** (Auto / Vacanță / Oprit / Vară).
- Un rând de butoane: **Pauză** și **Oaspeți** (pornit / oprit), **Vacanță**
  (deschide datele vacanței), **Reevaluează** și **Automat** (anulează toate
  modificările manuale). Un buton rămâne colorat cât modul lui e pornit.
- **Cald afară**, cât încălzirea e oprită pentru că e cald, cu motivul (media
  măsurată sau prognoza) sau când prognoza lasă încălzirea să pornească
  ([capitolul 6](06-vreme.ro.md)). Nu apare unde nu are efect: modul Oprit sau
  Vară, în afara sezonului, în pauză.
- O **bandă de pauză** sus cât casa e în pauză și o **bandă de oaspeți** cât
  modul oaspeți e pornit (cu sfârșitul lui, când are unul).
- În cardul compact, rândul pliat al casei arată persoanele, prezența
  (Acasă / Aproape / Departe), modul, temperatura de afară și o flacără cât
  există cerere de căldură.

## O cameră

Antetul arată numele, decizia (de exemplu *Aproape*, *Program*; în culoarea
nivelului) și flacăra și insignele pentru fereastră deschisă și modificare manuală,
plus *Risc de mucegai* (o picătură) cât e activă alerta de mucegai a camerei.

O **flacără** arată căldura peste tot (casa, camera deschisă, rândul pliat,
placa compactă): un cerc conturat cât există cerere de căldură (*Cere
căldură*), unul plin care pâlpâie cât sursa de căldură chiar merge
(*Încălzește*); cuvintele apar la atingere sau la mouse.

O cameră pliată (rând sau placă compactă) arată doar **nivelul** (de exemplu
*Eco*) și iconițe mici: încălzire (flacără), fereastră deschisă, risc de mucegai
(o picătură, cât e activă alerta lui), modificare manuală și modul oaspeți cât
e pornit; decizia apare când camera e deschisă, cu
nivelul lângă arc. Sub nume, placa compactă arată timpul până la țintă cât
camera încălzește, altfel următoarea schimbare (de exemplu *Somn · 22:00*).
Sub antet:

- un **arc** cu temperatura camerei și ținta sub ea; arcul e gol la antiîngheț
  și plin la temperatura maximă a camerei (doar arată temperatura, nu schimbă
  nimic); o liniuță scurtă de-a curmezișul arcului arată ținta pe aceeași scară
  (și pe arcurile mici); o **săgeată** în deschiderea arcului (și pe arcurile
  mici) arată că camera se încălzește (↑) sau se răcește (↓): o schimbare de
  cel puțin 0,2 °C pe oră în ultimele 30 de minute, adică un pas al unui
  senzor obișnuit (0,1 °C) în 30 de minute; fără săgeată cât e stabilă sau nu
  se știe încă (atributul `temperature_trend` al senzorului *Decizie*);
- lângă el **motivul** (în limba cardului), **timpul până la țintă** (de exemplu
  *~35 min*) sau, în timpul unei opriri anticipate, **temperatura estimată la
  schimbare** (*~21.5° la 22:00*), modul oaspeți cât e pornit, **După senzorul camerei** când e pornită pentru
  cameră și ce măsoară dispozitivul însuși (camerele cu TRV / dispozitive
  climate);
- **Azi**: profilul zilei ca bară pe ziua programului (de la *Ziua programului începe la*
  a casei, de exemplu 00 → 24 sau 04 → 04), cu ora de acum.
Dacă o cameră sub țintă nu încălzește, cardul spune de ce (*Nu încălzește: …*,
[capitolul 8](08-sursa-si-energie.ro.md#când-nu-încălzește-o-cameră-sub-țintă)).
Cât există o modificare manuală, butonul **Automat**, primul din rândul de
butoane de sub arc, o anulează (înapoi la automat).

Sub arc, butoanele deschid secțiunile **Temporar** (*Setează temporar*),
**Program**, **Grafic**, **Niveluri** (*Temperaturile nivelurilor*) și
**Detalii**, fiecare separat (pot fi deschise mai multe deodată);
butonul unei secțiuni deschise rămâne colorat. Butonul **Blocare** de lângă ele
pornește sau oprește blocarea modificărilor în cameră (colorat cât e pornită).
Graficul și secțiunile:

### Graficul

<p align="center"><img src="../images/card-chart.png" alt="Graficul: temperatura, ținta, încălzirea, temperatura de afară și temperatura prezisă" width="680"></p>

Se deschide cu butonul **Grafic** într-o fereastră peste dashboard, ca să aibă
loc (istoricul se încarcă doar atunci); câte o cameră pe rând. Se închide cu ✕,
cu un clic în afara ei, cu Esc și la trecerea pe altă pagină a dashboard-ului. Păstrează **7 zile** de istoric și
următoarele 12 ore și se deschide pe ultimele 24 de ore și următoarele 12:

- temperatura camerei;
- **temperatura prezisă** (punctat), după ce camera a învățat: modelul
  învățat al camerei (încălzire, curbă de temperatură, pierdere de căldură,
  soare, inerție) simulat minut cu minut după ținta planificată, cu prognoza
  orară. Încălzirea pornește și se oprește cum o face dispozitivul: Generic
  Thermostat după *cold* și *hot tolerance*, releele, controlul pornit / oprit
  și încălzirea după senzorul camerei după histerezis (și după inerția învățată, când e pornită),
  termostatele fără `hvac_action` după histerezis. Linia urcă și coboară în
  jurul țintei, cum face camera în realitate. Termostatele și TRV-urile
  comandate prin temperatură sau preset care raportează `hvac_action` se
  reglează singure: pentru ele, ca și pentru un Generic Thermostat configurat
  în YAML (toleranțele lui nu se pot citi), linia ține ținta, iar încălzirea
  prevăzută e o singură perioadă mai deschisă („încălzește cât îi trebuie”);
- ținta, ca linie în trepte, colorată după nivel;
- nivelurile planificate;
- perioadele în care camera a încălzit, pe o bandă separată, iar înainte, mai
  deschis, perioadele în care încălzește predicția;
- o linie fină la fiecare miezul nopții, între zile;
- temperatura de afară pe banda ei (măsurată, apoi prognoza orară punctat) și
  pragul de oprire ca linie punctată;
- **soarele** așteptat, ca o zonă galbenă discretă jos pe banda temperaturii
  de afară (de la deloc la soarele plin: la zenit pe cer senin), după ce
  camera a învățat că soarele o încălzește;
- următoarea pornire / oprire anticipată, ca perioadă umbrită.

Fiecare element din legenda de sub grafic ascunde sau arată seria lui la
atingere (tăiat cât e ascuns); alegerea se păstrează în acest browser pentru
toate graficele.

Valorile se citesc cu mouse-ul, la atingere sau trăgând pe grafic, într-o
căsuță opacă (și la temele cu carduri transparente). Zoom cu butoanele (1h, 6h,
−, +), dublu clic, ciupire sau Ctrl + rotiță, de la 20 de minute până la cele 7
zile; **⤢** revine la ultimele 24 de ore și următoarele 12. Deplasarea prin
istoric se face trăgând fereastra din **bara de navigare** de sub grafic sau
derulând lateral (touchpad sau Shift + rotiță). Bara de navigare apare cât
timp mouse-ul e peste grafic sau cât timp un deget e pe el și încă puțin după,
apoi dispare.

Partea planificată arată ce se va întâmpla: programul; o modificare manuală cu
durată până la sfârșitul ei; o vacanță planificată până la preîncălzire; un
eveniment din calendar până la sfârșitul lui. O fereastră, antiînghețul sau
mișcarea robinetelor apar doar pentru acum. Modul Oprit / Vară, pauza, plecarea,
senzorii căzuți și *Cald afară* apar așa cum sunt acum, pe toată perioada.

### Setează temporar

<p align="center"><img src="../images/card-light.png" alt="O modificare manuală cu Setează temporar deschis, temă deschisă" width="380"></p>

Se pune un nivel sau o temperatură pentru un număr de ore: *[Setează] [21] °C pentru
[2] h*. Ore goale = regula configurată pentru modificările manuale. O
modificare manuală cu sfârșit arată cât mai are, de exemplu *până la 15:10 ·
încă 1 h 30 min* (în pași de 5 minute peste o oră).

### Niveluri

Temperaturile nivelurilor (camerele fără Generic Thermostat) și temperatura
fixă pentru *aproape*. Se schimbă direct din card, între antiîngheț și maxim.

### Program

Fiecare profil cu zilele lui și un comutator pornit / oprit:

- **orele de început** se trag pe bara zilei, în pași de 5 minute, sau se scriu
  (ori se aleg) în câmpul de oră al fiecărui rând: bara se actualizează imediat,
  iar rândurile se reordonează când ieșiți din câmp;
- **nivelul** fiecărei ore se alege din lista de lângă ea;
- **zilele** se aleg în editor (toate, lucrătoare, weekend, zile anume);
- un profil se poate **copia** peste altul;
- cardul avertizează înainte ca pornirea sau oprirea unui profil să lase
  zile fără profil (care ar rămâne pe antiîngheț).

### Detalii

<p align="center"><img src="../images/card-details.png" alt="Detaliile camerei cu ce a învățat camera" width="380"></p>

Pe grupuri:

- **alertele** camerei și ale casei, primele;
- **Temperaturi**: camera, ținta, presetul termostatului, **umiditatea** (cu
  senzor de umiditate: a aerului și la peretele cel mai rece, marcată *risc de
  mucegai* de la 80 %), ajustările active, temperaturile nivelurilor;
- **Program**: următoarea pornire / oprire anticipată, timpul de încălzire;
- **Învățare**: starea ei (*învățat*, cu eroarea obișnuită a modelului, sau,
  în timpul învățării, două bare cu orele văzute cu și fără încălzire din cele
  4 necesare, cu valoarea implicită dedesubt) cu butonul **Resetează** (cu un
  al doilea clic pentru confirmare); după ce s-a învățat, câte o placă pentru
  **încălzire** (minutele pe grad acum, de exemplu *45 min/°C*), **inerție**
  (de exemplu *30 min*), **curba de temperatură** (de exemplu *+0.050 °C/h
  pentru fiecare °C mai frig afară* sau *fără*), **soare** (după ce s-a
  învățat) și **pierderea de căldură** (cât de repede scade camera acum);
- **Dispozitive**: fiecare entitate a camerei (termostate, relee, senzori de
  temperatură și umiditate, ferestre, ocupare, calibrare) cu rolul ei și
  starea de acum (*20.4° → 21.0° încălzește*, *deschisă*, *55 %*); una
  *indisponibilă*, *necunoscută* sau care *nu există* e marcată. La atingere
  se deschide fereastra ei.

La o modificare manuală, cardul arată unde a fost făcută (card / serviciu sau pe
dispozitiv), până când, *se aplică după: …* sau *revine după: …*.

Aproape orice valoare, stare sau insignă deschide la atingere fereastra cu
detaliile entității.

## Orele

Orele (grafic, bara programului, până când, datele vacanței) urmează setarea
*Fus orar* din profilul utilizatorului Home Assistant: al dispozitivului sau al
serverului, dacă acesta e ales. Datele vacanței se trimit cu fusul orar, ca să însemne același
moment pe server.

## Limba

Cardul e în engleză și română, după limba Home Assistant. Motivul deciziei și
numele ajustărilor sunt traduse (senzorul *Decizie* le are ca `reason_key` și
`reason_params`; `reason` rămâne textul în engleză).
