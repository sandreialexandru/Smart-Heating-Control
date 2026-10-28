<img src="custom_components/advanced_climate/brand/icon@2x.png" alt="Smart Heating Control" width="128" align="right">

# Smart Heating Control

[English](README.md) | **Română**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml)
[![Tests](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml)

Programe de încălzire pentru Home Assistant care țin cont de **prezență, zone,
ferestre, vreme și modificări manuale**, cu o singură decizie clară pentru
fiecare cameră și motivul ei.

Smart Heating Control este construită în jurul **Generic Thermostat**: folosește
aceleași nume de preseturi (`home`, `sleep`, `eco`, `away`, `comfort`,
`activity`) și doar îl alege pe cel potrivit; termostatul funcționează exact ca
înainte. Sunt acceptate și camere cu TRV-uri, alte termostate sau relee simple.

Numele setărilor și ale entităților sunt date mai jos în română, ca în
interfața Home Assistant în română.

> **Beta.** Integrarea rulează zilnic într-o singură casă: o zonă pentru toată
> casa cu Generic Thermostat și un releu, prezență, temperatura de afară cu
> oprirea când e cald și prognoza, programul intern și învățarea. TRV-urile, mai multe camere, alte termostate,
> camerele cu relee, o sursă de căldură pornită de integrare, tariful /
> fotovoltaicul și °F sunt acoperite de testele automate, dar încă nu de case
> reale. Dacă le încerci, te rog
> [spune-mi ce vezi](https://github.com/sandreialexandru/Smart-Heating-Control/issues/new/choose),
> fie că merge, fie că nu.

## Funcții

- **Prezență în trei stări**: *acasă*, *aproape* (de exemplu undeva în oraș)
  și *departe*. Zonele apropiate sunt evaluate și după coordonate, așa că o
  zonă ca „Birou” din oraș contează ca aproape, iar stările `not_home` rămase
  în urmă sunt corectate.
- **Programe** cu profiluri `workday` / `weekend` / pe zile ale săptămânii /
  personalizate, sărbători din integrarea Workday, profiluri alese dintr-un
  calendar, o oră de început a zilei pentru ture de noapte sau un Schedule
  helper existent.
- **Pornire / oprire anticipată** cu timpul de încălzire și răcirea învățate
  pentru fiecare cameră (vezi *Învățarea încălzirii* și *Învățarea
  răcirii și oprirea anticipată*). Odată începută, pornirea anticipată
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
- **Vizibilitate**: un senzor *Decizie* pentru fiecare cameră, cu regula
  câștigătoare și motivul, un eveniment la fiecare schimbare, diagnostic cu
  ultimele 100 de decizii și un card Lovelace cu program editabil.

**Ghidul complet**, pas cu pas și pe înțelesul tuturor (fiecare setare, fiecare
tip de încălzire, exemple): [docs/guide/README.ro.md](docs/guide/README.ro.md).
Specificația completă este în [docs/SPEC.ro.md](docs/SPEC.ro.md).

## Instalare

### HACS

1. HACS → ⋮ → **Custom repositories** → adaugă
   `https://github.com/sandreialexandru/Smart-Heating-Control` ca **Integration**.
2. Instalează **Smart Heating Control** și repornește Home Assistant.
3. **Setări → Dispozitive și servicii → Adaugă integrare → Smart Heating Control**.

### Manual

Copiază `custom_components/advanced_climate` în folderul
`config/custom_components` și repornește Home Assistant.

Necesită Home Assistant **2026.6.0** sau mai nou (cea mai veche versiune pe care rulează
testele; rulează și pe cea mai nouă).

## Configurare

> **Configurator interactiv:** [docs/configurator.html](https://github.com/sandreialexandru/Smart-Heating-Control/blob/main/docs/configurator.html) te duce prin
> fiecare formular pas cu pas, în engleză sau română, explică fiecare alegere
> și îți dă un rezumat cu ce ai de setat. Descarcă fișierul și deschide-l într-un
> browser.

1. **Creează casa**: întâi **unitatea de temperatură** (°C sau °F), apoi
   numele, persoanele, zonele apropiate și regula pentru acasă, apoi
   **încălzirea întregii case** (de exemplu Generic Thermostat-ul tău). Atât e
   suficient pentru o casă încălzită de un singur termostat: devine zona
   *Whole house* și folosește toate opțiunile. Se poate schimba mai târziu din
   *Configurează → Încălzirea întregii case*.
2. Opțional, **adaugă camere** cu *Adaugă cameră* pe pagina integrării, pentru
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
  termostate), apoi setările comenzii: histerezis și timpi minimi pentru relee
  și control on / off (releele au nevoie și de un senzor de temperatură în
  cameră), toleranța termostatului pentru comenzile prin temperatură / preset,
  nimic pentru Generic Thermostat.
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
2. Pauză – se trimite doar siguranța (și forțarea TRV e adusă înapoi la țintă)
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
*Blocare modificări* (comutator), *Anulează modificarea manuală*, *Resetează învățarea încălzirii* și
*Resetează învățarea răcirii* (butoane) și, pentru camerele
fără Generic Thermostat, temperaturile nivelurilor (numere).

## Învățarea încălzirii

*Explicația completă, cu exemple calculate și simulări: [docs/learning.ro.md](docs/learning.ro.md).*

Fiecare cameră învață cât durează să se încălzească, din propriile episoade de
încălzire:

**minute = parte fixă + grade × minute pe grad**, iar minutele pe grad urmează
temperatura de afară (o linie dreaptă).

- **Partea fixă** este timpul până începe camera să urce: pornește sursa de
  căldură, se încălzesc apa și caloriferele. Nu crește cu gradele, așa că și o
  recuperare mică, și o urcare mare după setback sunt estimate corect.
- **Minutele pe grad** și cum se schimbă ele cu temperatura de afară
  (pierderile de căldură, o centrală cu curbă de termoreglare) vin din aceleași
  episoade. O temperatură neîntâlnită încă e estimată din tendință (linia se
  prelungește); *Anticiparea maximă* a camerei limitează în continuare cât de
  devreme poate porni.

- Un **episod** începe când camera cere căldură și e cu cel puțin *toleranța*
  termostatului sub țintă, așa că se învață și ciclurile care doar mențin
  temperatura. Toleranța este *cold tolerance* al Generic Thermostat,
  *histerezisul* pentru relee și control on / off și setarea de cameră
  *Toleranța termostatului* pentru alte termostate (implicit 0). Episodul se
  încheie când se atinge ținta sau se oprește încălzirea; se folosește când
  cererea de căldură a durat cel puțin 10 minute și temperatura a crescut,
  oricât de puțin: se învață și o creștere lentă (poate arăta o problemă, dar
  e reală).
- Episoadele în care un **senzor de fereastră sau ușă** al camerei (sau unul
  legat din altă cameră) a fost deschis nu se folosesc. Camerele fără senzori
  de fereastră folosesc toate episoadele.
- Fiecare episod păstrează **gradele** urcate, **minutele** cât a durat și
  **temperatura medie de afară**. Ultimele 25 de episoade mici (sub 1 °C) și
  ultimele 25 mari (1 °C sau mai mult) se păstrează separat, așa că ciclurile
  mici și dese ale termostatului nu scot niciodată din memorie puținele urcări
  mari.
- Cele trei numere se calculează prin **metoda celor mai mici pătrate** din
  episoadele păstrate (din nou după fiecare episod). Un termen se folosește
  doar când episoadele îl pot deosebi: partea fixă cere episoade care diferă ca
  mărime cu cel puțin 1 °C, termenul de afară episoade la temperaturi de afară
  care diferă cu cel puțin 1 °C. Un rezultat imposibil (parte fixă negativă
  sau minute negative) se pune pe zero și restul se recalculează; departe de
  temperaturile învățate minutele pe grad nu scad niciodată sub zero. Când
  temperatura de afară nu se cunoaște, se folosește media episoadelor.
- Până la primul episod: 60 de minute pe grad, fără parte fixă.
- Versiunile dinainte de 2.0 păstrau doar o viteză pe episod; nu se poate
  converti, așa că după actualizare încălzirea se învață din nou (răcirea se
  păstrează).
- **Încălzire doar cât merge sursa de căldură.** Învățarea (încălzire și
  răcire) și timpul de încălzire consideră că o cameră încălzește doar cât
  merge sursa ei de căldură: Generic Thermostat încălzește (`hvac_action`),
  releul sau termostatul on / off e pornit și, când în opțiuni e setată o
  *Sursă de căldură* (centrala pe care o așteaptă TRV-urile și robinetele de
  zonă), doar cât merge și ea. O cameră care cere căldură în timp ce sursa
  așteaptă alte camere se răcește și e învățată ca răcire. Cât timp starea
  sursei e necunoscută, episoadele nu se folosesc. Cu TRV-uri și fără sursă
  setată se folosește cererea TRV-ului; e corect pentru o centrală care merge
  tot sezonul sau după compensarea exterioară. **Cu TRV-uri și o centrală
  pornită de un termostat care nu e în Home Assistant, învățarea nu e sigură:
  pornirea și oprirea anticipată nu sunt recomandate.**
- Încălzirea și răcirea se învață doar în **sezonul rece**: nu în modurile
  Oprit sau Vară și nici în afara sezonului de încălzire (episodul în curs
  este renunțat).
- **Cererea de căldură** vine din `hvac_action` (heating). Termostatele care nu
  îl raportează sunt considerate că încălzesc de la *histerezis* sub
  temperatura setată până la histerezis peste ea, ca un releu (oprirea
  anticipată folosește și ea histerezisul ca toleranță); pentru ele apare
  setarea *Histerezis* (și pentru termostatele indisponibile la configurare,
  care nu pot fi verificate).

Senzorii *Timp de încălzire* numără la fel: o cameră cât merge sursa ei de
căldură, casa cât merge sursa de căldură (fără ea, cât încălzește cel puțin o
cameră). Graficul din card arată aceste perioade.

Senzorul *Viteză de încălzire* arată **minutele pe grad** pentru temperatura de
afară de acum; atributele arată partea fixă (`fixed_minutes`), minutele pe grad
la −10 / 0 / 10 / 20 °C, schimbarea pe grad de afară, ce termeni se folosesc,
numărul de episoade (și al celor mari), cât de jos sub țintă începe un episod
și ultimele episoade. Pornirea anticipată folosește aceeași învățare. Cu *Camere necesare pentru pornirea sursei* mai
mare decât 1, o cameră aflată în pornire anticipată așteaptă până cer căldură
destule camere, deci poate ajunge la țintă mai târziu.

Cât timp o cameră e sub țintă, cardul arată sub temperatura țintă **timpul
până la țintă** (de exemplu *~35 min*), după încălzirea învățată pentru
temperatura de afară de acum; până la primul episod arată *se învață…*, cu
valoarea implicită folosită dedesubt (*implicit 60 min/1°C*).
Senzorul *Decizie* îl are ca atribut `time_to_target` (minute).

## Învățarea răcirii și oprirea anticipată

Răcirea se învață invers față de încălzire, pentru fiecare cameră (doar în
sezonul rece, vezi mai sus):

- Un **episod** începe când se oprește cererea de căldură (niciun senzor de
  fereastră sau ușă deschis) și se încheie când cererea de căldură reîncepe.
  Se folosește când a durat cel puțin 10 minute și temperatura a scăzut,
  oricât de puțin. Episoadele cu un senzor de fereastră deschis nu se
  folosesc.
- O cameră se răcește proporțional cu **diferența dintre interior și
  exterior**, așa că se învață un singur coeficient pe cameră (media ultimelor
  30 de episoade). Pereții, caloriferele și izolația nu sunt modelate: efectul
  lor e inclus în coeficientul măsurat al acelei case.

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

- Setarea de cameră *Oprire anticipată maximă* este limita; până la primul episod de
  răcire nivelul mai mic începe cu atât mai devreme.
- Odată începută, oprirea anticipată continuă până la ora din program;
  regulile de deasupra programului o pot suprascrie. Dacă înainte de acea oră
  camera coboară sub confortul nivelului curent (s-a răcit mai repede decât a
  învățat), oprirea anticipată se anulează: nivelul curent rămâne până la ora
  din program și oprirea nu mai pornește pentru acea schimbare. Dacă se
  întâmplă des, micșorează *Oprire anticipată maximă*.
- Cardul arată temperatura estimată la schimbare (de exemplu *~21.5° la
  22:00*), după răcirea învățată și temperatura de afară așteptată până
  atunci; senzorul *Decizie* o are ca atribut `stop_forecast`.
- Senzorul *Viteză de răcire* arată cât de repede scade camera acum fără
  încălzire; atributele arată coeficientul, episoadele și toleranța.

## Prognoza de afară pentru pornirea / oprirea anticipată

Cu o entitate meteo care are prognoză orară, pornirea și oprirea anticipată
folosesc **temperatura de afară așteptată cât timp rulează**, nu pe cea de
acum. Pentru o pornire la 05:00 pentru ora 07:00, timpul de încălzire este cel
învățat pentru media prognozei între 05:00 și 07:00; pentru o oprire, răcirea
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

Integrarea adaugă automat cardul la resursele dashboard-urilor
(`/advanced_climate/smart-heating-control-card.js?v=<versiune>`, actualizat la
fiecare versiune, ca browserele și aplicația companion să încarce noua
versiune). Cu dashboard-uri în mod YAML, adaugă singur acest URL ca resursă de
tip `module`. Cardul are editor vizual. Fără opțiuni arată toate casele și
camerele, cu toate comenzile:

```yaml
type: custom:smart-heating-control-card
```

| Opțiune | Implicit | Arată |
| --- | --- | --- |
| `title` | Încălzire | Titlul cardului (un text gol îl ascunde) |
| `rooms` | toate | Lista senzorilor *Decizie* ai camerelor de arătat |
| `show_house` | `true` | Prezența și persoanele, media temperaturii de afară (pe orele din *Medie pe*), sezonul, cererea de căldură, timpul de încălzire, modul (Auto / Vacanță / Oprit / Vară), Pauză, Oaspeți, datele vacanței, reevaluare și anularea tuturor modificărilor manuale |
| `show_rooms` | `true` | Camerele |
| `show_timeline` | `true` | Graficul ultimelor 24 de ore și al următoarelor 12: temperatura camerei, ținta (colorată după nivel), nivelurile planificate și perioadele în care camera s-a încălzit. Valorile se citesc cu mouse-ul, la atingere sau trăgând pe grafic. Zoom cu butoanele (1h, 6h, −, +), dublu clic, ciupire sau Ctrl + rotiță, până la 20 de minute; când e mărit, deplasarea în timp se face trăgând fereastra din bara de sub grafic (sau atingând un loc pe ea) |
| `show_quick_override` | `true` | Setează un nivel sau o temperatură pentru un număr de ore (gol = regula configurată) |
| `show_levels` | `true` | Temperaturile nivelurilor (camere fără Generic Thermostat, temperatura fixă pentru *aproape*) |
| `show_details` | `true` | Temperatura camerei și ținta, încălzirea învățată, timpul de încălzire, ajustările active, temperaturile nivelurilor |
| `show_schedule_editor` | `true` | Profilurile programului cu editor: orele de început se trag pe bara zilei (pași de 5 minute), un profil se copiază peste altă zi |
| `collapsed` | `false` | Camerele încep pliate; atinge numele camerei ca s-o deschizi |
| `compact` | `false` | Un rând pe cameră (nume, regulă, acum → țintă) și unul pentru casă; atinge un rând ca să-l deschizi |
| `runtime_period` | `day` | Timpul de încălzire arătat pentru `day`, `week` sau `month` (perioade calendaristice, din statisticile pe termen lung; atinge valoarea în card ca s-o schimbi). Senzorii *Timp de încălzire* rămân totaluri cumulate |

Fiecare cameră arată și decizia, motivul, insignele pentru încălzire /
fereastră / modificare manuală și *Înapoi la automat*; comutatorul *Blocare modificări*
este în *Setează temporar*. Secțiunile sunt, în ordine: *Setează temporar*,
*Niveluri*, *Program* (fiecare profil cu zilele lui și un comutator pornit /
oprit; zilele se aleg în editor) și *Detalii*.

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
  temperaturile nivelurilor); *Program* (următoarea pornire / oprire
  anticipată, timpul de încălzire); *Învățare* (încălzire: episoade, partea
  fixă și minutele pe grad acum; răcire: episoade și cât de repede scade camera
  acum; fiecare cu un buton **Resetează** care cere confirmare printr-un al
  doilea clic; ultimul episod de încălzire la sfârșit).
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


## Traduceri

Engleză și română (integrarea, cardul și această documentație).

## Licență

MIT
