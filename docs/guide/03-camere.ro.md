# 3. Camerele

*[English](03-rooms.md) · [Cuprins](README.ro.md)*

O **cameră** este o zonă de încălzire cu dispozitivele ei. Se adaugă pe pagina
integrării cu **Adaugă cameră** și se schimbă cu **⋮ → Reconfigurează camera**.
Zona *Whole house* (creată odată cu casa) se schimbă la fel.

Formularul are mai mulți pași. Pașii și câmpurile care nu se aplică tipului tău
de încălzire sunt săriți.

## Ce tip de încălzire alegi

| Ai… | Alege la *Încălzită prin* | Comanda |
| --- | --- | --- |
| Un **Generic Thermostat** pentru cameră | Generic Thermostat | – (GT își păstrează preseturile, integrarea doar le alege) |
| **TRV-uri** (robinete termostatice) | Alte termostate / TRV-uri | de obicei *Temperatură* |
| Un **termostat smart** cu preseturi proprii | Alte termostate / TRV-uri | *Preset* |
| Un termostat pe care vrei doar să-l pornești / oprești | Alte termostate / TRV-uri | *Pornit / oprit (hvac mode)* |
| Un **releu** (priză smart, releu Shelly / Sonoff, `input_boolean`) care pornește direct un radiator sau o centrală | Comutator (releu) | – (integrarea îl pornește și îl oprește singură) |

## Pasul 1: Cameră

| Câmp | Ce faci |
| --- | --- |
| **Nume** | Numele camerei, de exemplu „Dormitor”. |
| **Zonă** | Opțional, leagă camera de o zonă (area) din Home Assistant. |
| **Încălzită prin** | Tipul de încălzire, din tabelul de mai sus. |

## Pasul 2: Dispozitive

| Câmp | Ce faci |
| --- | --- |
| **Termostate** | Termostatele camerei (pentru Generic Thermostat și pentru alte termostate / TRV-uri). Mai multe termostate în aceeași cameră primesc toate aceeași comandă, de exemplu două TRV-uri pe două calorifere din sufragerie. |
| **Comutatoare (relee)** | Releele care încălzesc camera (doar pentru *Comutator*). |
| **Comandă** | Doar pentru alte termostate / TRV-uri, vezi mai jos. |

Trebuie ales cel puțin un dispozitiv (altfel apare *Alege cel puțin un
dispozitiv*).

**Un dispozitiv e comandat de o singură cameră.** Formularul refuză un termostat
sau un releu pe care îl comandă deja altă cameră (din orice casă), sursa de
căldură a unei case și releul unui Generic Thermostat folosit de altă cameră
(și releul unui Generic Thermostat ales aici, dacă e folosit în altă parte). Două
camere care trimit comenzi opuse aceluiași dispozitiv s-ar contrazice. Senzorii
(de temperatură, de fereastră, de ocupare) pot fi folosiți de mai multe camere.

### Comanda pentru alte termostate

| Comandă | Ce face integrarea | Potrivit pentru |
| --- | --- | --- |
| **Temperatură** | Trimite temperatura fiecărui nivel (de exemplu 21 °C pentru `home`). Termostatul o menține. | Cele mai multe TRV-uri |
| **Preset** | Fiecare nivel folosește un preset al termostatului, cu temperatura setată în termostat. | Termostate cu preseturi bine configurate |
| **Pornit / oprit (hvac mode)** | Termostatul doar e pornit și oprit; temperatura o ține integrarea, după senzorul camerei. | Termostate simple sau cu senzor prost așezat |

## Pasul 3: setările comenzii

### Releu sau *Pornit / oprit*: **Comandă pornit / oprit**

| Câmp | Implicit | Ce face |
| --- | --- | --- |
| Histerezis | 0,3 °C (0,1 – 3) | Pornește sub țintă − histerezis, oprește peste țintă + histerezis. Cu ținta aleasă 21 °C: pornește la 20,7 °C, oprește la 21,3 °C. |
| Timp minim pornit | 5 min (0 – 60) | Cel mai scurt timp cât rămâne pornit. 0 pentru radiatoare cărora nu le strică ciclurile scurte. |
| Timp minim oprit | 5 min (0 – 60) | Cea mai scurtă pauză între două porniri. |

Timpul minim se numără de la ultima comutare, **și de la una făcută de mână**.
Când se termină, camera e verificată din nou imediat. În banda de histerezis
(în exemplu, între 20,7 și 21,3 °C) releul rămâne în starea în care e: dacă
l-ai oprit tu, rămâne oprit.

### *Temperatură* sau *Preset*: **Termostat**

| Câmp | Implicit | Ce face |
| --- | --- | --- |
| Toleranța termostatului | 0 (0 – 2 °C) | Cât lasă termostatul camera să coboare sub țintă înainte să încălzească (toleranța lui proprie). Învățarea încălzirii pornește de la atât sub țintă. Dacă nu știi, lasă 0. |
| Histerezis | 0,3 °C | Apare doar dacă termostatul nu raportează când încălzește (`hvac_action`) sau e indisponibil la configurare. Atunci se consideră că încălzește de la histerezis sub temperatura setată până la histerezis peste ea, ca un releu. Se folosește pentru cererea de căldură, centrală, timpul de încălzire, învățare și ca toleranță a opririi anticipate. |
| Forțează temperatura TRV cât încălzește | oprit | Doar cu comanda *Temperatură*, vezi mai jos. |

### *Temperatură* cu **forțarea TRV**

Un TRV măsoară temperatura lângă calorifer, unde e mai cald decât în cameră, așa
că se poate închide înainte să se încălzească camera. Cu *Forțează temperatura
TRV cât încălzește* decide senzorul camerei, iar TRV-ul e ținut deschis cât
camera are nevoie de căldură:

- camera **cere căldură** de la ținta − histerezis și se oprește la ținta +
  histerezis, măsurat de **senzorii de temperatură ai camerei** (obligatorii,
  vezi pasul 5);
- cât cere căldură, TRV-urile primesc **Temperatura de forțare**; în rest
  primesc **ținta**, așa că TRV-ul se închide singur și ține camera și când Home
  Assistant e oprit.

| Câmp | Implicit | Ce face |
| --- | --- | --- |
| Temperatura de forțare | gol = temperatura maximă a casei | Trimisă TRV-urilor cât camera cere căldură. Între antiîngheț și maximul casei; niciodată sub țintă și niciodată peste maximul TRV-urilor. |
| Histerezis | 0,3 °C (0,1 – 3) | Banda cererii de căldură, ca la relee. Se cere aici sau pe pagina de dinainte, când TRV-ul nu raportează `hvac_action`. |

**Exemplu** (valorile alese în formular): ținta 20 °C, histerezis 0,2 °C,
maximul casei 25 °C, temperatura de forțare goală. La 20 − 0,2 = 19,8 °C în
cameră, TRV-urile primesc 25 °C; la 20 + 0,2 = 20,2 °C primesc iar 20 °C. Între
19,8 și 20,2 °C rămâne cum era.

Forțarea se aplică la orice cerere de căldură, și la antiîngheț. Fără forțare,
o cameră cu TRV-uri și senzori de temperatură e forțată doar pentru antiîngheț
(vezi [capitolul 9](09-ferestre-manual-siguranta.ro.md#antiînghețul)). La mișcarea
robinetelor, cu o fereastră deschisă și acțiunea *Oprire* sau în modul Oprit
cu dispozitive care se pot opri, nu există forțare. În **pauză** nu se trimite
nimic, doar că o forțare rămasă pe TRV-uri e adusă înapoi la țintă o dată, ca
niciun TRV să nu rămână forțat cât nu-l reglează nimic. Cardul o arată în
*Detalii* ca *Forțare TRV*.

### Generic Thermostat

Niciun pas: Generic Thermostat are propriile toleranțe (`cold_tolerance`,
`hot_tolerance`) și propriul timp minim.

## Pasul 4: Niveluri

| Câmp | Ce faci |
| --- | --- |
| **Când nimeni nu e acasă, dar cineva e aproape** | *Preset eco* (folosește nivelul `eco`) sau *Temperatură fixă* (o temperatură aleasă pe pagina următoare; la Generic Thermostat presetul devine `none`). |
| **Nu peste program** | Nebifat implicit. Bifat: când programul e mai jos decât nivelul sau temperatura pentru *aproape*, se aplică programul. Exemplu cu valori alese: *aproape* 20 °C, programul cere noaptea `sleep` 18 °C → 18 °C. Nebifat → 20 °C. |

Restul pasului depinde de tip:

- **Generic Thermostat**: nimic altceva. Temperaturile nivelurilor sunt cele
  setate în Generic Thermostat (`home_temp`, `sleep_temp`, `eco_temp`,
  `away_temp`, `comfort_temp`, `activity_temp`).
- **Comanda *Preset***: pentru fiecare nivel alegi **presetul termostatului**
  (lista arată preseturile găsite pe dispozitiv) și o **temperatură**.
  Termostatul își păstrează temperatura presetului. Dacă termostatul nu are un
  preset pentru un nivel, lași câmpul gol și se trimite temperatura
  nivelului.
- **Comanda *Temperatură*, *Pornit / oprit* și releele**: pentru fiecare nivel
  un **nume** (cum apare în program și în card; poți lăsa numele implicit) și o
  **temperatură**.

Temperaturile implicite: `home` 21, `sleep` 18, `eco` 17, `away` 12,
`comfort` 22, `activity` 20 °C. Ele pot fi între antiîngheț și temperatura
maximă a casei și se pot schimba oricând din card sau din entitățile număr ale
camerei. Două niveluri nu pot avea același nume.

**Exemplu de nume.** Pentru un birou poți numi `home` „Lucru” și `sleep`
„Închis”. În program scrii atunci `07:00 Lucru, 19:00 Închis`, iar rolurile
rămân aceleași: „Lucru” e tot nivelul `home`.

### Pagina **Aproape** (doar cu *Temperatură fixă*)

| Câmp | Implicit | Ce face |
| --- | --- | --- |
| Temperatură fixă pentru „aproape” | 17 °C | Trimisă cât nimeni nu e acasă și cineva e aproape. Se poate schimba din card. |

## Pasul 5: Senzori

| Câmp | Ce faci |
| --- | --- |
| **Senzori de temperatură** | Senzorii din cameră, folosiți în locul senzorului termostatului (mai exacți când termostatul stă lângă calorifer). Gol = senzorul termostatului. **Obligatorii pentru relee**, care nu au senzor (altfel apare *Releele au nevoie de un senzor de temperatură al camerei*), și pentru forțarea TRV (altfel apare *Forțarea TRV are nevoie de un senzor de temperatură al camerei*). Senzorul exterior al unei case e refuzat. Un senzor care nu raportează unitatea e citit în unitatea casei. |
| **Calibrare TRV** | Doar pentru TRV-uri și doar cu un senzor de cameră. *Offset*: corectează senzorul TRV-ului. *Temperatură externă*: scrie temperatura camerei în TRV (dacă TRV-ul are această intrare). *Oprit* altfel. |
| **Senzori de ocupare** | Senzori de mișcare / prezență ai camerei: dacă camera e goală un timp, trece pe `eco` chiar dacă e cineva acasă. Gol pentru camerele care urmează doar programul. |

Al doilea formular, **Senzori: detalii**, apare doar când e nevoie:

| Câmp | Implicit | Când apare | Ce face |
| --- | --- | --- | --- |
| Mai mulți senzori | Medie | cu mai mulți senzori de temperatură | *Medie*, *Minim* (cel mai rece) sau *Mediană*. |
| Entități de calibrare | – | cu calibrare | Entitățile număr ale TRV-urilor (offset sau temperatură externă). Integrarea găsește singură TRV-ul fiecărei entități (același dispozitiv). |
| Eco după lipsă de ocupare de | 30 min (1 – 720) | cu senzori de ocupare | Cât trebuie să fie goală camera până trece pe `eco`. |

**Exemplu de calibrare** (valori alese). TRV-ul spune 22 °C (e lângă
calorifer), senzorul de pe perete spune 20,5 °C, iar offsetul TRV-ului e acum 0.
Cu *Offset*, integrarea adaugă la offsetul actual diferența 20,5 − 22 = −1,5 °C,
deci scrie −1,5 °C, ca TRV-ul să „vadă” temperatura reală a camerei. Offsetul
se ajustează cel mult o dată la 10 minute, temperatura externă cel mult o dată
la 5 minute, și nimic în pauză.

**Ocuparea camerei.** Funcționează doar când programul cere un nivel mai cald
decât `eco`: o cameră goală nu ajunge niciodată mai caldă decât ar fi după
program.

## Pasul 6: Ferestre și uși

| Câmp | Ce faci |
| --- | --- |
| **Senzori de fereastră** | Ferestrele și ușile camerei. Oricare deschisă = fereastră deschisă. |
| **Ferestre din alte camere** | Ferestre care răcesc și camera aceasta, de exemplu ușa de balcon din sufragerie pentru hol. |
| **Detectează ferestrele deschise din temperatură** | O scădere rapidă a temperaturii e tratată ca fereastră deschisă 15 minute. Util pentru camere fără senzori de fereastră. |

Al doilea formular, **Ferestre: întârzieri și acțiune**:

| Câmp | Implicit | Ce face |
| --- | --- | --- |
| Întârziere la deschidere | 60 s (0 – 3600) | Cât trebuie să fie deschisă fereastra până reacționează încălzirea. Aerisirile mai scurte sunt ignorate. |
| Întârziere la închidere | 30 s (0 – 3600) | Cât se așteaptă după închidere până se încălzește din nou. |
| Când o fereastră e deschisă | Antiîngheț | *Antiîngheț* păstrează temperatura minimă. *Oprire* oprește încălzirea. |
| Scădere de temperatură | 1 °C (0,2 – 5) | Doar cu detectarea din temperatură: scăderea care contează ca fereastră deschisă. |
| În | 3 min (1 – 30) | Timpul în care trebuie să aibă loc scăderea. |

Exemplu cu valorile implicite ale detectării: dacă temperatura scade cu 1 °C în
3 minute, camera trece 15 minute pe acțiunea pentru fereastră deschisă.

Totul despre ferestre: [capitolul 9](09-ferestre-manual-siguranta.ro.md).

## Pasul 7: Program

| Câmp | Ce faci |
| --- | --- |
| **Sursa programului** | *Program intern* (scris aici sau editat din card) sau *Helper Program* (un Schedule helper din Home Assistant decide între două niveluri). |
| **Pornire anticipată** | Pornește încălzirea mai devreme, ca nivelul următor să fie atins la timp. Viteza de încălzire se învață în câteva zile. |
| **Oprire anticipată** | Coboară nivelul mai devreme înaintea unui nivel mai rece, cât de devreme se poate răci camera fără să iasă din confortul nivelului curent. Apare doar dacă în opțiunile casei există o temperatură de afară (senzor sau meteo). |

Apoi, după sursă:

- **Program** (intern): textul programului, un profil pe rând, de exemplu
  `workday: 00:00 sleep, 06:00 home, 22:00 sleep`. E mai ușor de editat din
  card. Un program greșit dă eroarea *Program invalid*.
- **Helper Program**: *Helper Program* (entitatea `schedule`), *Nivel cât
  helperul e pornit* (implicit `home`) și *Nivel cât helperul e oprit*
  (implicit `sleep`).

Cu pornirea sau oprirea anticipată pornită apare **Pornire / oprire
anticipată**:

| Câmp | Implicit | Ce face |
| --- | --- | --- |
| Anticipare maximă | 120 min (10 – 1440, adică până la 24 h) | Pornirea anticipată nu începe niciodată mai devreme de atât. |
| Oprire anticipată maximă | 30 min (5 – 1440, adică până la 24 h) | Oprirea anticipată nu începe niciodată mai devreme de atât. Până se învață răcirea, nivelul mai jos începe exact atât de devreme. |
| Toleranța opririi anticipate | 0 (0 – 2 °C) | Doar pentru termostatele care raportează `hvac_action` și nu sunt Generic Thermostat: cât poate coborî camera sub nivelul curent înainte de schimbare. 0 = camera nu are voie să scadă sub nivel, deci se oprește mai devreme doar când e mai caldă decât nivelul. |

Detalii: [capitolul 4](04-program.ro.md) și
[capitolul 7](07-anticipare-si-invatare.ro.md).

## Pasul 8: Extra

| Câmp | Când apare | Ce face |
| --- | --- | --- |
| **Câștig solar** | doar cu o entitate meteo în opțiunile casei | Valoare negativă (de exemplu −1 °C, între −3 și 0) care coboară ținta cât e soare, pentru camerele care se încălzesc de la soare. 0 = oprit. |
| **Mișcarea robinetelor** | doar pentru TRV-uri care nu sunt comandate *Pornit / oprit* | Deschide TRV-urile complet 5 minute o dată pe săptămână, contra depunerilor, în orice mod (și vara). |

Cu mișcarea robinetelor pornită apare **Mișcarea robinetelor**: *Ziua*
(implicit duminică) și *Ora* (implicit 10:00; ideal când nu e nevoie de
căldură).

## Exemple complete

### Dormitor cu Generic Thermostat

1. *Cameră*: nume „Dormitor”, *Încălzită prin* Generic Thermostat.
2. *Dispozitive*: `climate.dormitor` (entitatea Generic Thermostat).
3. *Niveluri*: *Preset eco*.
4. *Senzori*: nimic (GT are deja senzorul lui).
5. *Ferestre*: senzorul ferestrei dormitorului.
6. *Program*: intern, cu pornire anticipată.

Temperaturile se schimbă în setările Generic Thermostat (presetările lui).

### Sufragerie cu două TRV-uri

1. *Încălzită prin* Alte termostate / TRV-uri.
2. *Dispozitive*: cele două TRV-uri, *Comandă* Temperatură.
3. *Termostat*: toleranța 0.
4. *Niveluri*: temperaturile (de exemplu `home` 21,5 °C).
5. *Senzori*: un senzor pe perete, *Calibrare TRV* Offset, apoi la detalii
   entitățile de offset ale celor două TRV-uri.
6. *Ferestre*: ușa de balcon.
7. *Program*: intern, cu pornire și oprire anticipată.
8. *Extra*: mișcarea robinetelor duminică la 10:00.

Cu TRV-uri, centrala trebuie să știe când să pornească: la opțiunile casei,
*Sursa de căldură*, alegi centrala sau releul ei (vezi
[capitolul 8](08-sursa-si-energie.ro.md)).

### Baie cu radiator electric pe o priză smart

1. *Încălzită prin* Comutator (releu).
2. *Dispozitive*: `switch.priza_baie`.
3. *Comandă pornit / oprit*: histerezis 0,3 °C, timpi minimi 0 (un radiator
   electric nu are nevoie de ei).
4. *Niveluri*: de exemplu `home` 23 °C.
5. *Senzori*: senzorul de temperatură al băii (obligatoriu).

### Termostat smart cu preseturi proprii

1. *Încălzită prin* Alte termostate / TRV-uri, *Comandă* Preset.
2. *Niveluri*: pentru `home` presetul „Comfort” al termostatului, pentru
   `sleep` presetul „Night”, pentru `away` presetul „Away”; ce lipsește rămâne
   gol și se trimite ca temperatură.

## Entitățile unei camere

Fiecare cameră primește un dispozitiv cu entitățile ei: decizia, ținta,
temperatura camerei, următoarea schimbare, învățarea, timpul de încălzire,
fereastra, cererea de căldură, modificarea manuală, blocarea pentru copii și,
pentru camerele fără Generic Thermostat, temperaturile nivelurilor. Lista
completă: [capitolul 11](11-entitati-si-servicii.ro.md).
