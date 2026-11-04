# Smart Heating Control – referință

*[English](reference.md) · [README](../README.ro.md) · [Ghid](guide/README.ro.md)*

Tot ce face integrarea, în detaliu tehnic: ce face fiecare regulă, senzor, serviciu și opțiune a cardului. Pentru o introducere pas cu pas există [ghidul](guide/README.ro.md).

## Funcții

- **Prezență în trei stări**: *acasă*, *aproape* (de exemplu undeva în oraș)
  și *departe*. Zonele apropiate sunt evaluate și după coordonate, așa că o
  zonă ca „Birou” din oraș contează ca aproape, iar stările `not_home` rămase
  în urmă sunt corectate.
- **Programe** cu profiluri `workday` / `weekend` / pe zile ale săptămânii /
  personalizate, sărbători din integrarea Workday, profiluri alese dintr-un
  calendar, o oră de început a zilei pentru ture de noapte sau un Schedule
  helper existent.
- **Pornire / oprire anticipată** cu un model termic învățat pentru fiecare
  cameră: încălzire, pierdere de căldură și inerție termică (detalii în
  *Învățarea* și *Oprirea anticipată*). Odată începută, pornirea anticipată
  continuă până la ora din program, chiar dacă camera s-a încălzit mai
  devreme; regulile de deasupra programului o pot suprascrie.
- **Ferestre**: întârzieri la deschidere / închidere, antiîngheț sau oprit,
  detectare după o scădere bruscă a temperaturii, ferestrele camerelor
  vecine, alerte.
- **Vreme**: prag de oprire după temperatura exterioară, cu mediere și
  histerezis (timpul de mediere este și cât rămâne valabilă o valoare de afară
  când senzorul sau meteo e indisponibil; după el temperatura de afară e
  necunoscută), sezon de încălzire (date sau automat), compensare după
  temperatura de afară, prognoză, câștig solar pe cameră (are nevoie de
  entitatea meteo a casei; setarea apare doar atunci). Media măsurată
  pe ultimele *Medie pe* ore oprește încălzirea când atinge pragul; încălzirea
  poate porni din nou când acea medie scade la temperatura de repornire
  (prag − histerezis). Cu *Folosește prognoza* contează și media prognozei pe
  următoarele *Ore de prognoză* (niciodată o singură oră din prognoză):
  - încălzire oprită de media măsurată, media prognozei la temperatura de
    repornire sau sub ea: încălzirea poate porni (o după-amiază caldă nu mai
    ține încălzirea oprită într-o seară rece); media prognozei peste
    temperatura de repornire: încălzirea rămâne oprită;
  - încălzire pornită, media prognozei la prag sau peste: încălzirea se
    oprește mai devreme și rămâne oprită până când acea medie scade la
    temperatura de repornire (același histerezis ca la media măsurată); o
    medie sub prag nu o oprește. Mai multe *Ore de prognoză* o opresc mai
    devreme înaintea unei perioade calde.

  În medie, fiecare valoare din prognoză e valabilă pentru ora ei; până la
  următoarea oră din prognoză contează valoarea măsurată. Pragul, histerezisul,
  *Medie pe* și *Ore de prognoză* vin toate din opțiuni. Fără prognoză decide
  doar media măsurată.
- **Modificări manuale**: detectate automat și păstrate o durată fixă sau până
  la următoarea reevaluare (schimbare de program, prezență, fereastră sau mod).
  Un dispozitiv care doar raportează mai târziu valorile trimise de integrare
  (de exemplu un TRV Zigbee pe baterie) nu e o modificare manuală. Dacă între
  timp o regulă de mai sus (fereastră, antiîngheț) schimbă dispozitivele,
  valoarea manuală se pune din nou după aceea. Blocare pentru copii, pauză și
  butoane de anulare pe cameră și pentru toată casa.
- **Moduri globale**: Auto, Vacanță (cu date, preîncălzire înainte de
  întoarcere și vacanță automată), Oprit (antiîngheț) și Vară. În orele de
  preîncălzire dinaintea sfârșitului vacanței se aplică programul chiar dacă
  toată lumea e încă departe. Doar cu data de sfârșit: vacanța începe acum.
  Vacanța automată se termină când cineva e pe drum spre casă (*arriving*),
  ca să se preîncălzească; revine doar când toți sunt din nou departe cât e
  setat la *Vacanță automată după departe timp de*.
- **Energie**: tarif dinamic, surplus fotovoltaic, comanda sursei de
  căldură (centralei) după cererea de căldură a camerelor, statistici ale
  timpului de încălzire.
- **Siguranță**: antiîngheț mereu (odată ce încălzește, continuă până când
  dispozitivul nu mai cere căldură; o cameră în antiîngheț pornește singură
  sursa de căldură, și în pauză; cu un senzor în cameră se decide după cameră,
  iar TRV-urile sunt forțate să se deschidă), temperatură maximă, verificarea comenzilor
  cu reîncercare, alerte pentru dispozitive indisponibile, senzori defecți,
  baterii descărcate și ferestre deschise, mișcarea robinetelor TRV.
- **Alertă de risc de mucegai** pentru o cameră cu senzor de umiditate (și o
  temperatură de afară a casei): umiditatea la peretele cel mai rece, după
  metoda DIN 4108-2 (peretele la afară + 0,70 × (cameră − afară), formula
  Magnus); 80 % sau mai mult timp de o oră o declanșează, sub 75 % se încheie.
- **Vizibilitate**: un senzor *Decizie* pentru fiecare cameră, cu regula
  câștigătoare și motivul, un eveniment la fiecare schimbare, diagnostic cu
  ultimele 100 de decizii și un card Lovelace cu program editabil.

**Ghidul complet**, pas cu pas și pe înțelesul tuturor (fiecare setare, fiecare
tip de încălzire, exemple): [docs/guide/README.ro.md](guide/README.ro.md).
Specificația completă este în [docs/SPEC.ro.md](SPEC.ro.md).

## Instalare

### HACS

1. HACS → ⋮ → **Custom repositories**: se adaugă
   `https://github.com/sandreialexandru/Smart-Heating-Control` ca **Integration**.
2. Se instalează **Smart Heating Control** și se repornește Home Assistant.
3. **Setări → Dispozitive și servicii → Adaugă integrare → Smart Heating Control**.

### Manual

Folderul `custom_components/advanced_climate` se copiază în
`config/custom_components`, apoi se repornește Home Assistant.

Necesită Home Assistant **2026.6.0** sau mai nou (cea mai veche versiune pe care rulează
testele; rulează și pe cea mai nouă).

## Configurare

> **Configurator interactiv:** [docs/configurator.html](configurator.html) parcurge
> fiecare formular pas cu pas, în engleză sau română, explică fiecare alegere
> și dă la sfârșit un rezumat cu tot ce trebuie setat. Fișierul se descarcă și
> se deschide într-un browser.

1. **Crearea casei**: întâi **unitatea de temperatură** (°C sau °F), apoi
   numele, persoanele, zonele apropiate și regula pentru acasă, apoi
   **încălzirea întregii case** (de exemplu Generic Thermostat-ul existent). Atât e
   suficient pentru o casă încălzită de un singur termostat: devine zona
   *Whole house* și folosește toate opțiunile. Se poate schimba mai târziu din
   *Configurează → Încălzirea întregii case*.
2. Opțional, **se adaugă camere** cu *Adaugă cameră* pe pagina integrării, pentru
   camerele cu robinete sau termostate proprii. Fiecare cameră are propriile
   dispozitive, senzori, ferestre și program. Zona *Whole house* se schimbă la
   fel (*⋮ → Reconfigurează* pe pagina integrării).
3. Restul se află în **opțiunile** integrării (prezență, zile lucrătoare și
   calendar, vreme și sezon, energie, centrală, modificări manuale și vacanță,
   alerte).

### Unitatea de temperatură

Fiecare casă are o singură unitate de temperatură, °C sau °F, pentru toate
camerele ei. Toate temperaturile casei se introduc și se afișează în ea:
setările, temperaturile nivelurilor, senzorii, cardul și serviciul
`set_override`. Se alege prima la crearea casei și se schimbă cu
**Reconfigurează** pe pagina integrării; valorile sunt convertite, nimic nu
trebuie introdus din nou. Integrarea își păstrează valorile în °C și convertește
citirile și comenzile termostatelor și senzorilor din unitatea fiecăruia, așa
că unitatea casei nu trebuie să fie aceeași cu cea a Home Assistant.

Fiecare formular arată doar ce se aplică. Întâi vin alegerile; un al doilea
formular cere apoi doar valorile de care au nevoie și e sărit când nu se aplică
nimic:

- **Încălzire**: sursa, apoi dispozitivele ei (și comanda pentru alte
  termostate), apoi setările comenzii: histerezis, timpi minimi și *Folosește
  inerția învățată* pentru relee și control on / off (releele au nevoie și de un senzor de temperatură în
  cameră), histerezisul pentru comenzile prin temperatură / preset doar când
  termostatul nu raportează `hvac_action`, nimic pentru Generic Thermostat.
- **Camere**: calibrarea TRV și mișcarea robinetelor doar pentru TRV-uri;
  temperatura fixă pentru *aproape* doar cu această alegere; agregarea doar cu
  mai mulți senzori de temperatură; timpul de ocupare doar cu senzori de
  ocupare; întârzierile ferestrelor doar cu senzori de fereastră sau cu
  detectarea după scăderea temperaturii; câmpurile Schedule helper doar pentru
  un helper; limitele pornirii / opririi anticipate doar când sunt activate.
- **Opțiuni**: distanțele de preîncălzire doar cu un senzor Proximity / de timp
  de călătorie, valorile pentru prag / prognoză / sezon / compensare doar
  pentru ce e activat, pragurile de preț și fotovoltaic doar cu senzorii lor,
  timpii sursei de căldură doar cu o sursă, durata fixă doar pentru acel tip de
  modificare manuală.

### Formatul programului

Un profil pe rând, fiecare interval este `HH:MM preset`:

```
workday: 00:00 sleep, 06:00 home, 22:00 sleep
weekend: 00:00 sleep, 08:00 home, 23:00 sleep
```

Fiecare profil are **zilele lui** și este **pornit sau oprit** (se setează în
card, *Program*): toate zilele, zile lucrătoare, weekend și sărbători, sau zile
anume. O zi folosește, în această ordine: un eveniment de calendar cu numele
unui profil (și un profil oprit; un eveniment care acoperă o parte din zi îl
alege pentru toată ziua, azi la fel ca în zilele următoare, ca planul și
pornirea anticipată de mâine să corespundă cu ce se întâmplă mâine) → profilul activ al acelei zile (de exemplu un
profil pentru miercuri are prioritate față de cel de zile lucrătoare doar
miercurea) → profilul activ al zilelor lucrătoare sau al weekendului → profilul
activ pentru toate zilele. Pornirea unui profil le oprește pe cele active cu care
se suprapune („toate zilele” se suprapune cu zilele lucrătoare și cu weekendul;
zilele anume se suprapun când au o zi comună), deci o zi nu are niciodată două.

O zi **neacoperită de niciun profil activ rămâne pe antiîngheț**; camera
afișează o alertă (*Fără profil activ în program: …*), iar cardul avertizează
înainte ca pornirea sau oprirea unui profil să lase astfel de zile. Profilurile
salvate înainte de 2.2 își păstrează zilele: `mon` … `sun` pentru ziua lor,
`workday` și `weekend` pentru tipul lor de zi (pentru toate zilele când lipsește
celălalt), iar când niciunul nu există primul profil e pentru toate zilele;
celelalte pornesc oprite. Selectorul *Profile* al camerelor a fost eliminat în
2.2.

### Cum decide o cameră

Regulile sunt evaluate de sus în jos; prima care se aplică decide:

1. Siguranță (antiîngheț, temperatură maximă) – aplicată mereu, și unei
   modificări manuale și în pauză (un nivel peste maxim se trimite ca maxim);
   antiînghețul pornește singur sursa de căldură
2. Pauză – se trimite doar siguranța (și o temperatură mai mare lăsată de încălzirea după senzorul camerei e adusă înapoi la țintă)
3. Mișcarea robinetelor – în orice mod, nu cu o fereastră deschisă
4. Mod Oprit / Vară / în afara sezonului de încălzire
5. Fereastră deschisă
6. Modificare manuală
7. Vacanță (într-o zi fără profil activ: antiîngheț)
8. Prezență: departe → `away` (într-o zi fără profil activ: antiîngheț),
   aproape → `eco` (sau o temperatură fixă; cu *Nu peste program* cea mai mică
   dintre ea și program)
9. Program (pornire / oprire anticipată, ocuparea camerei)

Apoi ajustările (prag de temperatură exterioară, compensare, tarif,
fotovoltaic, câștig solar) și limitele de siguranță.

## Entități

Casă: *Mod* (select), *Prezență* (acasă / aproape / departe), *Pauză* și
*Mod oaspeți* (comutatoare), *Început / Sfârșit vacanță* (dată și oră), *Heating
season*, *Cald afară* și *Cerere de căldură* (senzori binari), *Medie afară*,
*Timp de încălzire*, butoane pentru anularea modificărilor manuale, anularea
vacanței și reevaluare.

Cameră: *Decizie* (enum, cu motivul în atribute), *Temperatură țintă*, *Room
temperature*, *Următoarea schimbare*, *Viteză de încălzire*, *Viteză de răcire*, *Heating
runtime*, *Cerere de căldură*, *Fereastră deschisă*, *Modificare manuală*,
*Blocare modificări* (comutator), *Anulează modificarea manuală*, *Resetează învățarea*
(butoane) și, pentru camerele
fără Generic Thermostat, temperaturile nivelurilor (numere).

## Învățarea

*Explicația completă, cu exemple calculate și simulări: [docs/learning.ro.md](learning.ro.md).*

Fiecare cameră își învață un mic model fizic, continuu, cu și fără încălzire:

**creștere pe oră = (încălzire − curbă × afară) × q − pierdere × (cameră − afară) + câștig solar × soare**

- **Încălzirea** (`heating_per_hour`): °C pe oră adăugate de încălzire la toată
  căldura, la 0 °C afară.
- **Curba de temperatură** (`weather_curve`): câte °C pe oră în plus adaugă
  încălzirea pentru fiecare °C mai frig afară: pozitivă la o centrală cu
  compensare după exterior, negativă la o pompă de căldură care dă mai puțin
  la ger, 0 la o temperatură fixă a apei sau la un radiator electric. Se învață
  după ce camera a încălzit la temperaturi de afară diferite cu cel puțin 1 °C
  (abatere standard); până atunci și într-o casă fără temperatură de afară
  este 0.
- **Pierderea de căldură** (`loss_per_hour`): partea din diferența interior /
  exterior pierdută pe oră (cu cât e mai frig afară, cu atât mai repede).
- **Câștigul solar** (`sun_gain`): °C pe oră adăugate de soare la un semnal
  solar de 1. Semnalul este sin(înălțimea soarelui) × (1 − 0,75 × acoperirea
  cu nori^3,4), din oră, locația din Home Assistant și norii entității meteo
  (0 noaptea, 1 cu soarele la zenit pe cer senin). Se învață doar cu o
  entitate meteo și doar când se vede clar (la cel puțin 5 erori standard de
  0); altfel e 0. Nu se setează nicio orientare.
- **Inerția** (`inertia_minutes`): q, partea din încălzire care ajunge în
  cameră, urmează pornirea / oprirea încălzirii cu această întârziere:
  centrala, apa, caloriferele sau pardoseala se încălzesc întâi după pornire
  și mai dau căldură după oprire. Se învață, nu se setează: zece candidați
  (0 – 240 de minute) se învață împreună și se folosește cel care prezice cel
  mai bine camera.
- Fiecare **30 de minute** de măsurători sunt o ecuație; încălzirea, curba,
  pierderea și câștigul solar sunt soluția ei prin **metoda celor mai mici pătrate**. Intervalele
  mai vechi contează mai puțin (pe jumătate după 7 zile), deci modelul urmează
  o cameră care se schimbă; un interval departe de ce așteaptă modelul (peste
  de 2,5 ori diferența obișnuită: o ușă lăsată deschisă, gătitul) contează mai
  puțin.
- Nu se folosesc: intervalele cu un **senzor de fereastră sau ușă** al camerei
  (sau unul legat) deschis, cu starea sursei de căldură necunoscută, în timpul
  exercițiului robinetelor, cu temperatura de afară necunoscută la o casă care
  o are sau în afara **sezonului rece** (modurile Oprit sau Vară, în afara
  sezonului de încălzire).
- Modelul se folosește după **4 ore cu încălzire și 4 fără** (de obicei în
  prima zi); până atunci 60 de minute pe grad, fără inerție.
- Fără temperatură de afară în casă, pierderea se învață ca o constantă (°C pe
  oră).
- Toate predicțiile (pornirea anticipată, timpul până la țintă, oprirea
  anticipată, temperatura așteptată la schimbare) sunt o simulare minut cu
  minut a modelului, de la temperatura camerei și căldura care ajunge acum în
  cameră.
- Învățarea versiunilor dinainte de 2.6 (episoade) nu se potrivește modelului
  și se renunță la ea: după actualizare fiecare cameră învață din nou.
- **Încălzire doar cât merge sursa de căldură.** Învățarea (încălzire și
  răcire) și timpul de încălzire consideră că o cameră încălzește doar cât
  merge sursa ei de căldură: Generic Thermostat încălzește (`hvac_action`),
  releul sau termostatul on / off e pornit și, când în opțiuni e setată o
  *Sursă de căldură* (centrala pe care o așteaptă TRV-urile și robinetele de
  zonă), doar cât merge și ea. O cameră care cere căldură în timp ce sursa
  așteaptă alte camere se răcește și asta se învață ca pierdere de căldură.
  Cât timp starea sursei e necunoscută, nu se învață nimic. Cu TRV-uri și fără sursă
  setată se folosește cererea TRV-ului; e corect pentru o centrală care merge
  tot sezonul sau după compensarea exterioară. **Cu TRV-uri și o centrală
  pornită de un termostat care nu e în Home Assistant, învățarea nu e sigură:
  pornirea și oprirea anticipată nu sunt recomandate.**
- **Cererea de căldură** vine din `hvac_action` (heating). Termostatele care nu
  îl raportează sunt considerate că încălzesc de la *histerezis* sub
  temperatura setată până la histerezis peste ea, ca un releu (oprirea
  anticipată folosește și ea histerezisul ca toleranță); pentru ele apare
  setarea *Histerezis* (și pentru termostatele indisponibile la configurare,
  care nu pot fi verificate).

Senzorii *Timp de încălzire* numără la fel: o cameră cât merge sursa ei de
căldură, casa cât merge sursa de căldură (fără ea, cât încălzește cel puțin o
cameră). Graficul din card arată aceste perioade.

Senzorul *Viteză de încălzire* arată **minutele pe grad** cu încălzirea
pornită, la temperatura camerei și cea de afară de acum; atributele arată
modelul (`heating_per_hour`, `weather_curve`, `loss_per_hour`, `constant_loss`,
`inertia_minutes`, `heat_reaching_now`, `error_per_hour`), minutele pe grad la
−10 / 0 / 10 / 20 °C afară și progresul învățării (`hours_heating`,
`hours_idle`, `hours_needed`). Pornirea anticipată folosește același model. Cu *Camere necesare pentru pornirea sursei* mai
mare decât 1, o cameră aflată în pornire anticipată așteaptă până cer căldură
destule camere, deci poate ajunge la țintă mai târziu.

Cât timp o cameră e sub țintă, cardul arată sub temperatura țintă **timpul
până la țintă** (de exemplu *~35 min*), după model și temperatura de afară de
acum; până se învață modelul arată *se învață…*, cu
valoarea implicită folosită dedesubt (*implicit 60 min/1°C*).
Senzorul *Decizie* îl are ca atribut `time_to_target` (minute).

## Oprirea anticipată

**Oprirea anticipată** are nevoie de o temperatură de afară (senzor sau
entitatea meteo a casei; fără ea opțiunea nu apare, nu se face oprire
anticipată, iar valorile de afară salvate înainte se șterg). Coboară nivelul
înainte de următorul mai rece cât de devreme se poate răci camera rămânând în
confortul nivelului curent la ora din program. Confortul este *toleranța*:
*cold tolerance* al Generic Thermostat, *histerezisul* pentru relee, control
on / off și termostatele care nu raportează `hvac_action`, și setarea de cameră
*Toleranța opririi anticipate* pentru celelalte termostate (implicit 0).
Exemplu: home 22 °C până la 22:00, toleranță 0,5 °C, afară 7 °C: dacă camera
scade de la 22 la 21,5 °C în 40 de minute, sleep începe la 21:20.

- Setarea de cameră *Oprire anticipată maximă* este limita; până se învață
  modelul, nivelul mai mic începe cu atât mai devreme.
- Cât poate sta camera fără căldură se simulează cu pierderea de căldură și
  inerția învățate (caloriferele calde încă dau căldură după oprire).
- Odată începută, oprirea anticipată continuă până la ora din program;
  regulile de deasupra programului o pot suprascrie. Dacă înainte de acea oră
  camera coboară sub confortul nivelului curent (s-a răcit mai repede decât a
  învățat), oprirea anticipată se anulează: nivelul curent rămâne până la ora
  din program și oprirea nu mai pornește pentru acea schimbare. Dacă se
  întâmplă des, *Oprire anticipată maximă* trebuie micșorată.
- Cardul arată temperatura estimată la schimbare (de exemplu *~21.5° la
  22:00*), după model și temperatura de afară așteptată până
  atunci; senzorul *Decizie* o are ca atribut `stop_forecast`.
- Senzorul *Viteză de răcire* arată cât de repede scade camera acum fără
  încălzire (gol până se învață); atributele arată pierderea, inerția și
  toleranța.

## Prognoza de afară pentru pornirea / oprirea anticipată

Cu o entitate meteo care are prognoză orară, pornirea și oprirea anticipată
folosesc **temperatura de afară așteptată cât timp rulează**, nu pe cea de
acum. Pentru o pornire la 05:00 pentru ora 07:00, timpul de încălzire se
simulează cu media prognozei între 05:00 și 07:00; pentru o oprire, răcirea
folosește media prognozei din perioada opririi. Perioada depinde de acea
temperatură, așa că se recalculează de câteva ori (3 treceri) pornind de la
perioada găsită înainte. Fiecare valoare din prognoză e valabilă pentru ora ei;
până la următoarea oră din prognoză se folosește temperatura de afară măsurată.

Fără entitate meteo, fără prognoză orară sau când prognoza nu ajunge până la
schimbare, se folosește temperatura de afară de acum, ca înainte. Prognoza se
citește la fiecare 30 de minute când entitatea meteo e setată și o folosește
pragul de oprire după prognoză sau o cameră cu pornire / oprire anticipată.

Cardul arată următoarea pornire sau oprire anticipată în *Detaliile* camerei
(de exemplu *Pornire pentru presetul home (21.0°) la 07:00: începe pe la 05:10, afară
prognozat 2.4°*, sau *Pornire pentru temperatura 21.0° la …* când nivelul se trimite ca temperatură; *în curs din …* după ce a început; *se învață…* până se învață ceva).
Senzorul *Decizie* o are ca atribut `next_estimate`: `kind` (`optimal_start` /
`optimal_stop`), `at` (schimbarea), `preset`, `minutes`, `starts_at`,
`started_at`, `outdoor`, `outdoor_source` (`forecast` / `now`), `learned`,
`sent_as` (`preset` / `temperature`) și `temperature` (a nivelului).
Apare doar când opțiunea e activă pentru cameră și următoarea schimbare e mai
caldă (pornire) sau mai rece (oprire); oprirea anticipată mai are nevoie de o
temperatură de afară cunoscută și să nu fie anulată pentru acea schimbare.

## Servicii

| Serviciu | Descriere |
| --- | --- |
| `advanced_climate.set_override` | Setează un preset sau o temperatură ca modificare manuală (durată opțională) |
| `advanced_climate.clear_override` | Anulează modificările manuale (o cameră sau toate) |
| `advanced_climate.set_vacation` | Setează sau anulează perioada de vacanță |
| `advanced_climate.reevaluate` | Evaluează totul acum |
| `advanced_climate.set_schedule` | Înlocuiește programul unei camere (text sau profiluri) |

Camerele se aleg cu `room` (nume sau id) sau prin oricare dintre entitățile
lor.

Evenimentul `advanced_climate_decision_changed` apare de fiecare dată când o
cameră își schimbă decizia (`room`, `old_rule`, `rule`, `old_target`, `target`,
`reason`).

## Cardul Lovelace


*Pozele folosesc date inventate; cardul e în limba Home Assistant (aici engleză).*

Integrarea adaugă automat cardul la resursele dashboard-urilor
(`/advanced_climate/smart-heating-control-card.js?v=<versiune>`, actualizat la
fiecare versiune, ca browserele și aplicația companion să încarce noua
versiune). Cu dashboard-uri în mod YAML, acest URL se adaugă manual ca resursă de
tip `module`. Cardul are editor vizual. Fără opțiuni arată toate casele și
camerele, cu toate comenzile:

```yaml
type: custom:smart-heating-control-card
```

| Opțiune | Implicit | Arată |
| --- | --- | --- |
| `title` | Încălzire | Titlul cardului (un text gol îl ascunde) |
| `rooms` | toate | Lista senzorilor *Decizie* ai camerelor de arătat |
| `show_house` | `true` | Prezența și persoanele (cercuri în culoarea locului unde sunt), plăci pentru media temperaturii de afară (pe orele din *Medie pe*), sezon, cererea de căldură și timpul de încălzire, modul (Auto / Vacanță / Oprit / Vară) și un rând de butoane: Pauză și Oaspeți (pornit / oprit; modul oaspeți arată o bandă sus), Vacanță (deschide datele), Reevaluează, Automat (anulează toate modificările manuale) |
| `show_rooms` | `true` | Camerele |
| `show_timeline` | `true` | Un buton **Grafic** în fiecare cameră care deschide, într-o fereastră peste dashboard, graficul: 7 zile de istoric și următoarele 12 ore, deschis pe ultimele 24 de ore și următoarele 12: temperatura camerei, temperatura prezisă de modelul învățat (încălzirea pornită și oprită ca de dispozitiv: toleranțele GT, histerezisul, inerția învățată; ținta ținută la termostatele care se reglează singure), ținta (colorată după nivel), nivelurile planificate și perioadele în care camera s-a încălzit. Valorile se citesc cu mouse-ul, la atingere sau trăgând pe grafic (într-o căsuță opacă). Zoom cu butoanele (1h, 6h, −, +), dublu clic, ciupire sau Ctrl + rotiță, de la 20 de minute până la cele 7 zile (⤢ revine); deplasarea prin istoric se face trăgând fereastra din bara de navigare de sub grafic (vizibilă cât timp mouse-ul sau un deget e pe grafic) sau derulând lateral. Sub grafic, fiecare element din legendă ascunde sau arată seria lui (se păstrează în browser). După ce camera a învățat că soarele o încălzește, soarele așteptat (`sun_forecast`, de la 0 la 1) e o zonă galbenă discretă pe banda temperaturii de afară |
| `show_quick_override` | `true` | Setează un nivel sau o temperatură pentru un număr de ore (gol = regula configurată) |
| `show_levels` | `true` | Temperaturile nivelurilor (camere fără Generic Thermostat, temperatura fixă pentru *aproape*) |
| `show_details` | `true` | Temperatura camerei și ținta, învățarea (două bare de progres în timpul învățării; apoi câte o placă pentru încălzire, inerție, curba de temperatură, soare și pierderea de căldură), timpul de încălzire, ajustările active, temperaturile nivelurilor |
| `show_schedule_editor` | `true` | Profilurile programului cu editor: orele de început se trag pe bara zilei (pași de 5 minute), un profil se copiază peste altul |
| `collapsed` | `false` | Camerele încep pliate (un rând cu un arc mic, numele, timpul până la țintă, iconițe de stare, nivelul și ținta); camera se deschide atingând rândul |
| `compact` | `false` | O placă pe cameră (numele, iconițele de stare, arc cu temperatura, nivel, țintă; sub nume timpul până la țintă cât încălzește, altfel următoarea schimbare) și un rând pentru casă; se deschide la atingere |
| `runtime_period` | `day` | Timpul de încălzire arătat pentru `day`, `week` sau `month` (perioade calendaristice, din statisticile pe termen lung; se schimbă și atingând valoarea în card). Senzorii *Timp de încălzire* rămân totaluri cumulate |

Fiecare cameră arată și decizia, o flacără (conturată cât cere căldură, plină și pâlpâind cât
încălzește; și la casă și la camerele pliate) / insignele pentru fereastră / modificare manuală, un arc cu temperatura camerei (gol la
antiîngheț, plin la maxim; doar arată valoarea), o săgeată ↑ / ↓ în deschiderea lui cât camera se încălzește sau se răcește (`temperature_trend`: cel puțin 0,2 °C/h în ultimele 30 de minute) și ținta, motivul, timpul până
la țintă, încălzirea după senzorul camerei când e pornită, ce măsoară dispozitivul însuși, profilul
zilei ca bară și un buton *Automat* (înapoi la automat) în rândul de butoane cât există o modificare manuală. Butoanele de sub arc deschid *Temporar* (setează
temporar; o modificare manuală cu sfârșit arată cât mai are), *Program* (fiecare profil cu zilele lui și un comutator pornit /
oprit; zilele se aleg în editor), *Grafic*, *Niveluri* (temperaturile nivelurilor) și *Detalii*, fiecare separat (mai
multe deodată) și un buton *Blocare* pentru blocarea modificărilor în cameră.

- **Nu încălzește**: sub țintă, camera spune de ce nu încălzește (în toleranța
  termostatului sau în histerezis, timp minim pornit / oprit, așteaptă alte
  camere sau camera de referință, sursa de căldură oprită sau necunoscută,
  termostatul oprit). Senzorul *Decizie* îl are ca `no_heat_reason`.
- **Cald afară**: cât încălzirea e oprită pentru că e cald, casa arată de ce,
  de exemplu *Cald afară: pornit • încălzirea e oprită până media scade la
  16°*, *pornit (prognoză) • încălzirea e oprită: media prognozei pe 3 h este
  19.2°*, sau cât prognoza lasă încălzirea să pornească *anulat (prognoză) • vine frigul: media prognozei pe 3 h
  este 12.4°, camerele încălzesc la nevoie*; senzorul *Medie afară* are
  `cutoff_reason` (`measured`, `forecast_warm`, `forecast_cold`) și
  `forecast_mean`. Nu apare unde pragul nu are efect: modul Oprit sau
  Vară, în afara sezonului de încălzire și în pauză (în Vacanță rămâne:
  *away* încă încălzește).
- **Grafic**: partea planificată urmează ce se va întâmpla: programul; o
  modificare manuală cu durată până la sfârșitul ei; o vacanță planificată până
  la preîncălzire și un eveniment din calendar până la sfârșitul lui, apoi
  programul; fereastra, antiînghețul sau exercitarea ventilelor doar pentru
  acum (programul în continuare); modul Oprit / Vară, în afara sezonului,
  pauza, toți plecați sau în apropiere, senzorii picați și cald afară așa cum
  sunt acum, pe toată perioada.
- **Grafic**: temperatura de afară pe o bandă separată (măsurată, apoi
  prognoza orară punctat; pragul de oprire ca linie punctată) și următoarea
  pornire / oprire anticipată ca perioadă umbrită, cu ora de început (niciodată
  mai lungă decât permit setările camerei); în ea ținta programată este deja
  nivelul următor, iar tooltip-ul arată *Pornire anticipată* / *Oprire
  anticipată* deasupra ei.
- **Pauză**: o bandă sus pe card cât timp casa e în pauză (comutatorul *Pauză*
  rămâne singurul control).
- **Detalii**, pe grupuri: alertele camerei și ale casei (primele, în limba
  cardului); *Temperaturi* (camera, ținta, presetul termostatului, ajustările,
  umiditatea aerului și la peretele cel mai rece cu senzor de umiditate,
  temperaturile nivelurilor); *Program* (următoarea pornire / oprire
  anticipată, timpul de încălzire); *Învățare* (starea sau progresul, cu un
  buton **Resetează** care cere confirmare printr-un al doilea clic; după ce s-a
  învățat, încălzirea: minutele pe grad acum și inerția; curba de temperatură;
  soarele, după ce s-a văzut: câștigul lui și cât adaugă acum; pierderea de
  căldură: cât de repede scade camera acum).
- **Modificare manuală**: unde a fost făcută (card / serviciu sau pe dispozitiv),
  până când, *se aplică după: …* cât timp o regulă de mai sus ține o schimbare
  din card departe de dispozitive și *revine după: …* cât timp o regulă de mai
  sus o întrerupe.
- Următoarea pornire / oprire anticipată apare doar cât camera urmează
  programul; camerele reci sunt semnalate doar în acele camere.
- **Linkuri**: valorile, stările, insignele și detaliile deschid fereastra cu
  detaliile entității.
- **Limbă**: motivul deciziei și numele ajustărilor apar în limba cardului
  (senzorul *Decizie* le are ca `reason_key` și `reason_params`; `reason`
  rămâne textul în engleză).
