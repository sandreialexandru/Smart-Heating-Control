# 2. Instalarea și casa

*[English](02-install-and-house.md) · [Cuprins](README.ro.md)*

## Ce e necesar

- Home Assistant **2026.6.0** sau mai nou.
- Dispozitivele de încălzire în Home Assistant: un Generic Thermostat, TRV-uri,
  alte termostate sau relee.
- Recomandat: aplicația Home Assistant pe telefon pentru fiecare persoană (ca
  integrarea să știe cine e acasă), un senzor de temperatură exterioară sau o
  entitate meteo.

## Instalarea

**Cu HACS (recomandat):**

1. HACS → meniul ⋮ → **Custom repositories**: se adaugă
   `https://github.com/sandreialexandru/Smart-Heating-Control`, tipul
   **Integration**.
2. Se caută **Smart Heating Control**, se instalează și se repornește Home
   Assistant.
3. **Setări → Dispozitive și servicii → Adaugă integrare → Smart Heating
   Control**.

**Manual:** folderul `custom_components/advanced_climate` se copiază în
`config/custom_components`, apoi se repornește Home Assistant.

Cardul Lovelace se adaugă singur la resursele dashboard-urilor
([capitolul 10](10-card.ro.md)).

## Ce configurare aleg pentru casa mea?

Înainte de a crea casa, răspundeți la două întrebări: **ce o încălzește** și
**cine poate porni centrala**. Configurarea are trei piese:

1. **Încălzirea întregii case** (zona *Întreaga casă*): un singur termostat sau
   releu care încălzește toată locuința. Primește programul casei, ca o cameră.
2. **Camerele**: calorifere sau zone cu dispozitivul lor (TRV, termostat,
   releu, radiator electric) și, ideal, cu senzorul lor. Fiecare e o cameră cu
   programul ei.
3. **Sursa de căldură**: centrala (releul ei sau termostatul care o pornește)
   atunci când camerele nu o pot porni singure. E necesară doar cu **TRV-uri**
   sau vane de zonă: un TRV doar deschide sau închide robinetul caloriferului;
   dacă nimeni nu pornește centrala, caloriferul rămâne rece.

**Regula.** Cu camere cu TRV, integrarea are nevoie de **o cale proprie spre
centrală**: un releu al centralei sau termostatul care o pornește, ca *Sursă de
căldură*. Un dispozitiv folosit deja de zona *Întreaga casă* sau de o cameră nu
poate fi și *Sursă de căldură* (un dispozitiv, un singur rol: altfel două părți
ale integrării ar comanda același dispozitiv).

| Locuința | Încălzirea întregii case | Camere | Sursa de căldură |
| --- | --- | --- | --- |
| **Un termostat sau releu pentru toată locuința, fără TRV-uri** (de exemplu un apartament cu Generic Thermostat pe centrală) | Generic Thermostat, Alte termostate sau Comutator (releu) | – | – (nu se oferă cu Generic Thermostat sau releu) |
| **TRV-uri pe calorifere, centrala are un releu în Home Assistant** | Încă fără dispozitive | câte una pentru fiecare cameră cu TRV | **releul centralei** |
| **TRV-uri pe calorifere, centrala e pornită de un termostat din Home Assistant** (Hive, Nest, Tado, Netatmo) | Încă fără dispozitive | câte una pentru fiecare cameră cu TRV | **acel termostat**, cu *Boost pentru sursa de căldură* pornit |
| **TRV-uri doar pe unele calorifere, un termostat pornește centrala** (de exemplu un termostat pe hol) | Încă fără dispozitive | camerele cu TRV | **acel termostat**, cu *Boost* pornit și o *Temperatura sursei în repaus* (de exemplu 17,5 °C) pentru caloriferele fără TRV |
| **Radiatoare electrice, aer condiționat, pompă de căldură în fiecare cameră** | Încă fără dispozitive | câte una pentru fiecare cameră, cu releul sau termostatul ei | – (fiecare cameră se încălzește singură) |
| **Un singur radiator electric sau aer condiționat pentru toată locuința** | Comutator (releu) sau Alte termostate | – | – |
| **Un termostat sau un releu pe toată casa și TRV-uri în unele camere** | termostatul sau releul | camerele cu TRV | ⚠️ nu se poate: vezi mai jos |

**De ce ultimul caz e limitat.** Zona întregii case pornește centrala doar după
senzorul ei. Când la acel senzor e cald și o cameră cu TRV e rece, TRV-ul se
deschide, dar centrala nu pornește, deci caloriferul rămâne rece. Dispozitivul
întregii case nu poate fi și sursă de căldură (are deja un rol). Soluții:
**releul centralei ca *Sursă de căldură*** în loc de pe toată casa (cu un
termostat care pornește și el centrala, un releu legat în paralel cu el); sau
termostatul folosit ca *Sursă de căldură* în loc de pe toată casa (rândurile de
mai sus), cu o temperatură de repaus pentru caloriferele fără TRV.

**Cu TRV-uri pe toate caloriferele**, instalația trebuie să lase apa să treacă
când toate se închid: un bypass automat, o centrală cu bypass intern sau un
calorifer fără TRV (de obicei în baie).

**Exemple.**

- *Un apartament, un Generic Thermostat comută releul centralei, fără TRV-uri*:
  Încălzirea întregii case = Generic Thermostat. Nimic altceva; pagina *Sursa
  de căldură* nici nu apare.
- *O casă, un releu Shelly pe centrală, TRV-uri în toate camerele*: Încă fără
  dispozitive; câte o cameră pentru fiecare cameră cu TRV (*Alte termostate /
  TRV-uri*, cu forțarea TRV când camera are senzorul ei); *Sursa de căldură* =
  releul Shelly.
- *O casă, un Hive pe hol legat la centrală, TRV-uri în trei camere*: Încă fără
  dispozitive; trei camere cu TRV; *Sursa de căldură* = Hive, *Boost pentru
  sursa de căldură* pornit, *Temperatura sursei în repaus* 17,5 °C. Hive ține
  restul casei la circa 17,5 °C și primește maximul când o cameră cu TRV cere
  căldură.
- *Radiatoare electrice pe prize inteligente*: Încă fără dispozitive; câte o
  cameră pentru fiecare cameră (*Comutator (releu)*, cu senzorul ei de
  temperatură); fără sursă de căldură.

## Crearea casei

Formularele arată doar câmpurile care se aplică. Dacă un câmp nu apare, înseamnă
că nu are sens pentru alegerile făcute.

### Pasul 1: casa

| Câmp | Ce se completează |
| --- | --- |
| **Unitatea de temperatură** | °C sau °F. Toate temperaturile casei se introduc și se afișează în ea. Se poate schimba mai târziu (mai jos). |
| **Nume** | Numele casei, de exemplu „Acasă”. Apare pe dispozitive și în card. |
| **Persoane** | Entitățile `person` ale celor care locuiesc în casă. Locația lor decide dacă starea casei e *acasă*, *aproape* sau *departe*. Dacă rămâne gol, starea casei e mereu *acasă* și decide doar programul. |
| **Zone apropiate** | Zonele în care starea casei e *aproape* (`eco`) în loc de *departe* (`away`), de exemplu zona orașului. Dacă rămâne gol, există doar *acasă* și *departe*. |
| **Starea casei e „acasă” când** | *Cel puțin o persoană e acasă* (potrivit pentru aproape toate casele) sau *Toți sunt acasă* (încălzirea scade imediat ce pleacă cineva). |

**Exemplu.** Andrei și Maria locuiesc în București. Se aleg persoanele
`person.andrei` și `person.maria`, iar ca zonă apropiată o zonă „București”
(creată în Home Assistant la *Setări → Zone*). Când amândoi sunt la muncă în
oraș, starea casei e *aproape* și camerele trec pe `eco`. Când pleacă din oraș, starea casei e
*departe* și camerele trec pe `away`.

### Pasul 2: încălzirea întregii case

**Încălzită prin** alege ce încălzește toată casa:

| Alegere | Când se folosește |
| --- | --- |
| **Generic Thermostat** | Un Generic Thermostat pornește centrala (cazul cel mai des întâlnit). |
| **Alte termostate / TRV-uri** | Un termostat smart care nu e Generic Thermostat (de exemplu un termostat Zigbee sau Wi-Fi). |
| **Comutator (releu)** | Un releu pornește direct încălzirea, fără termostat. |
| **Încă fără dispozitive** | Nimic nu încălzește toată casa ca o singură zonă; fiecare cameră se adaugă cu încălzirea ei: TRV-uri sau robinete pe calorifere, radiatoare electrice, pompă de căldură sau aer condiționat, încălzire în pardoseală. |

Ce se alege aici devine zona **Whole house** (toată casa), care se comportă ca o
cameră și folosește toate opțiunile casei.

**Pasul 3: dispozitive.** În funcție de alegere:

- **Termostate**: termostatul care comandă centrala, de exemplu entitatea
  Generic Thermostat.
- **Comutatoare (relee)**: doar când un releu încălzește direct.
- **Comandă**: doar pentru alte termostate decât Generic Thermostat; în
  [capitolul 3](03-camere.ro.md#comanda-pentru-alte-termostate) pentru
  diferența dintre *Temperatură*, *Preset* și *Pornit / oprit*.

**Pasul 4: setările comenzii.** Apare doar când e nevoie:

- **Comandă pornit / oprit** (releu, sau termostat comandat *Pornit / oprit*):
  - *Senzori de temperatură*: senzorii din cameră. Obligatorii pentru relee,
    care nu au senzor propriu.
  - *Histerezis* (implicit 0,3 °C): încălzirea pornește sub țintă minus
    histerezis și se oprește peste țintă plus histerezis. Exemplu cu ținta
    aleasă 21 °C: pornește la 21 − 0,3 = 20,7 °C și se oprește la
    21 + 0,3 = 21,3 °C.
  - *Timp minim pornit* și *Timp minim oprit* (implicit 0, fără așteptare): se
    setează (de exemplu câteva minute) când releul pornește o centrală fără
    protecție proprie la cicluri scurte sau ca să fie cruțat un releu mecanic;
    0 e potrivit pentru radiatoarele electrice.
  - *Folosește inerția învățată* (implicit pornit): după ce s-a învățat,
    încălzirea se oprește și pornește puțin mai devreme în interiorul benzii,
    după cât de încet reacționează (vezi [capitolul 3](03-camere.ro.md#releu-sau-pornit--oprit-comandă-pornit--oprit)).
- **Termostat** (alte termostate comandate prin *Temperatură* sau *Preset*),
  doar dacă termostatul nu spune când încălzește (nu are `hvac_action`):
  - *Histerezis*. Atunci integrarea consideră că încălzește de la
    histerezis sub temperatura setată până la histerezis peste ea.
- **Generic Thermostat**: niciun pas, GT are propriile setări.

După acești pași casa e creată. Pentru o casă cu un singur termostat,
configurarea e gata; restul e opțional.

## Schimbarea unității de temperatură

Pe pagina integrării, la casă: **⋮ → Reconfigurează**. Se alege altă unitate, iar
toate valorile (setări, niveluri, card) se convertesc. Nu trebuie introdus
nimic din nou.

## Opțiunile casei

Pe pagina integrării, **Configurează** deschide un meniu cu grupurile de
opțiuni. Fiecare grup are întâi alegerile, apoi, dacă e cazul, un al doilea
formular doar cu valorile necesare.

### Încălzirea întregii case

Aceiași pași ca la crearea casei (sursa, dispozitivele, setările comenzii).
Restul setărilor zonei *Whole house* (niveluri, senzori, ferestre, program) se
schimbă ca la orice cameră: pe pagina integrării, la zona *Whole house*,
**⋮ → Reconfigurează** ([capitolul 3](03-camere.ro.md)).

### Prezență

| Setare | Implicit | Ce face |
| --- | --- | --- |
| Persoane | – | Ca la crearea casei. |
| Starea casei e „acasă” când | cel puțin una | Ca la crearea casei. |
| Zone apropiate | niciuna | Ca la crearea casei. |
| Folosește coordonatele pentru zonele apropiate | pornit | Cineva aflat într-o zonă care e în interiorul unei zone apropiate (de exemplu zona „Birou” din oraș) contează ca *aproape*. Se oprește dacă persoanele nu au locație GPS. |
| Întârziere la plecare | 10 min | Cât timp trebuie să lipsească toată lumea înainte să scadă încălzirea. Evită reacția la drumuri scurte (magazin, plimbatul câinelui). |
| Întârziere la sosire | 0 min | De obicei 0: încălzirea revine imediat ce vine cineva. Se mărește doar dacă GPS-ul raportează uneori greșit „acasă”. |
| Senzori de prezență | niciunul | Țin starea casei *acasă* cât sunt pornite (mmWave, mișcare, un comutator pentru cine nu are telefon). |
| Modul oaspeți se oprește după | 0 h | Modul oaspeți ține starea casei *acasă*; se oprește singur după atâtea ore. 0 = doar manual. |
| Senzor de distanță (Proximity) | – | Pentru preîncălzirea pe drum spre casă. |
| Senzor de direcție (Proximity) | – | Ca preîncălzirea să pornească doar când cineva vine spre casă, nu când stă la un birou aproape de casă. |
| Senzor de timp de deplasare | – | Timpul până acasă (Waze, Google Travel Time). |

Cu un senzor de distanță sau de timp, apare al doilea formular,
**Preîncălzire pe drum spre casă**:

| Setare | Implicit | Ce face |
| --- | --- | --- |
| Preîncălzește sub distanța | 10 km | Preîncălzirea pornește când cineva e mai aproape de atât. |
| Preîncălzește sub timpul | 20 min | Preîncălzirea pornește când cineva e la mai puțin de atâtea minute de casă. |

Totul despre prezență: [capitolul 5](05-prezenta.ro.md).

### Zile lucrătoare și calendar

| Setare | Implicit | Ce face |
| --- | --- | --- |
| Senzor Workday | – | Senzorul integrării Workday, ca sărbătorile să folosească profilul zilelor de weekend. Fără el, luni–vineri sunt zile lucrătoare. |
| Calendar | – | Opțional. Un eveniment cu numele unui profil (de exemplu `home_office`) sau al unui nivel (de exemplu `away`) îl aplică. |
| Ziua programului începe la | 00:00 | De obicei 00:00. Se schimbă doar pentru ture de noapte, ca o noapte să aparțină zilei de dinainte. |

Detalii: [capitolul 4](04-program.ro.md).

### Vreme și sezon

| Setare | Implicit | Ce face |
| --- | --- | --- |
| Senzor de temperatură exterioară | – | Temperatura de afară. Dacă e gol, se folosește temperatura entității meteo. |
| Entitate meteo | – | Pentru prognoză, câștigul solar și ca temperatură de afară când nu există senzor. |
| Oprește încălzirea când e cald afară | oprit | Oprește încălzirea când media de afară atinge pragul. |
| Folosește prognoza | oprit | Folosește media prognozei pe următoarele ore pentru oprire / repornire. |
| Sezon de încălzire | Mereu | *Mereu*, *Între date* sau *Automat (temperatura exterioară)*. |
| Compensare exterioară | oprit | Ridică puțin ținta când e foarte frig afară. |
| Ignoră ferestrele peste | – | Peste această temperatură de afară, ferestrele deschise nu mai reduc încălzirea. |

**Ce cere fiecare opțiune.** Oprirea când e cald, sezonul *Automat*, compensarea
și *Ignoră ferestrele peste* au nevoie de un senzor de temperatură exterioară sau
de o entitate meteo. *Folosește prognoza* are nevoie de o entitate meteo și de
oprirea când e cald pornită. Fără ele formularul nu se salvează și arată eroarea
lângă opțiune. Dacă o configurare mai veche le are pornite fără sursă, casa dă
alerta *Pornite, dar nu funcționează…*, iar sezonul *Automat* se comportă ca
*Mereu* (nu rămâne blocat oprit).

Al doilea formular, **Valori pentru vreme și sezon**, arată doar ce e pornit:

| Setare | Implicit | Interval |
| --- | --- | --- |
| Prag de oprire (exterior) | 18 °C | 5 – 30 °C |
| Histerezis prag | 1 °C | 0 – 5 °C |
| Medie pe | 6 h | 1 – 48 h |
| Ore de prognoză | 3 h | 1 – 24 h |
| Început / sfârșit sezon (LL-ZZ) | 10-15 / 04-15 | luna-ziua |
| Sezon automat: zile consecutive | 3 | 1 – 14 |
| Prag sezon automat | 15 °C | 0 – 25 °C |
| Compensează sub | −5 °C | −30 – 15 °C |
| Compensare | 0,5 °C | −3 – 3 °C |

Totul despre vreme: [capitolul 6](06-vreme.ro.md).

### Energie

| Setare | Ce face |
| --- | --- |
| Senzor preț energie | Prețul energiei (tarif dinamic). Gol cu preț fix. |
| Senzor surplus fotovoltaic | Puterea trimisă în rețea (W). Util doar cu încălzire electrică sau pompă de căldură. |

Al doilea formular, **Praguri pentru energie**:

| Setare | Implicit | Ce face |
| --- | --- | --- |
| Preț mare de la | – | La acest preț sau peste se aplică ajustarea la preț mare. |
| Ajustare la preț mare | −1 °C | De obicei negativă. |
| Preț mic până la | – | La acest preț sau sub se aplică ajustarea la preț mic. |
| Ajustare la preț mic | +0,5 °C | De obicei pozitivă. |
| Surplus de la | 1000 W | De la acest surplus se aplică ajustarea. |
| Ajustare cu surplus | +0,5 °C | Grade adăugate cât există surplus. |

Detalii: [capitolul 8](08-sursa-si-energie.ro.md).

### Sursa de căldură și cererea de căldură

Nu apare în meniu când zona *Whole house* e Generic Thermostat sau releu: acea
zonă pornește deja centrala (o sursă salvată înainte se scoate la salvarea
încălzirii întregii case).

| Setare | Implicit | Ce face |
| --- | --- | --- |
| Sursa de căldură | – | Centrala (sau releul care o pornește) când camerele nu o pot porni singure (TRV-uri, robinete de zonă). Formularul refuză un dispozitiv al unei camere și releul unui Generic Thermostat folosit de o cameră. |

Al doilea formular, doar cu o sursă de căldură:

| Setare | Implicit | Ce face |
| --- | --- | --- |
| Camere necesare pentru pornirea sursei | 1 | Câte camere trebuie să ceară căldură ca să pornească sursa. Cel mult numărul de camere ale casei; dacă mai târziu se șterg camere și rămân mai puține, apare o alertă. |
| Timp minim pornită / oprită | 0 / 0 min | 0 = sursa urmează imediat cererea de căldură. O valoare mai mare protejează de cicluri scurte o centrală fără protecție proprie. |
| Boost pentru sursa de căldură | pornit | Doar pentru un termostat (`climate`) ca sursă: temperatura maximă a casei ca să pornească, antiînghețul casei ca să se oprească, mereu pe încălzire. Oprit: i se schimbă doar modul. |
| Temperatura sursei în repaus | – (antiîngheț) | Doar cu boost: ce primește termostatul cât nicio cameră nu cere căldură, de exemplu 17,5 °C când încălzește și calorifere fără TRV. Sub maximul casei. |
| Cameră de referință | – | Doar această cameră decide când merge sursa; celelalte doar își deschid sau închid robinetele. |

Detalii: [capitolul 8](08-sursa-si-energie.ro.md).

### Modificări manuale, vacanță și limite

| Setare | Implicit | Ce face |
| --- | --- | --- |
| Modificările manuale se păstrează | Durată fixă | *Durată fixă* (orele de mai jos) sau *Până la următoarea reevaluare* (până se schimbă programul, prezența, o fereastră sau modul). |
| Modificarea manuală se aplică | Doar acea cameră | *Toată casa* copiază o modificare manuală în toate camerele; doar când fiecare cameră are robinete proprii. Apare doar cu mai multe camere. |
| Preîncălzire înainte de sfârșitul vacanței | 4 h | Programul revine cu atâtea ore înainte de sfârșitul vacanței. |
| Vacanță automată după departe timp de | 0 h (oprit) | Vacanța pornește singură după ce toți au fost departe atâtea ore. Apare doar când casa are persoane. |
| Antiîngheț | 7 °C (3 – 15 °C) | Cea mai mică temperatură. Camerele cu Generic Thermostat folosesc în locul ei temperatura minimă a GT. |
| Temperatură maximă | 25 °C (15 – 35 °C) | Nicio țintă nu trece de ea. |
| Verificare periodică la | 5 min (1 – 60) | Verificarea de siguranță care retrimite decizia. Schimbările se aplică oricum imediat. |

Cu *Durată fixă* apare **Durată fixă** (implicit 2 h, între 0,25 și 72 h).

Detalii: [capitolul 9](09-ferestre-manual-siguranta.ro.md) și
[capitolul 5](05-prezenta.ro.md#vacanța).

### Alerte

| Setare | Implicit | Ce face |
| --- | --- | --- |
| Alerte importante către | – | Telefoane (`notify.mobile_app_...`), email sau alte servicii de notificare. Pentru email se scriu adresele după serviciu: `notify.eu_gmail_com: ana@exemplu.ro, ion@exemplu.ro` (Google Mail are nevoie de ele). Se trimit imediat, și în orele de liniște. Gol = notificări în Home Assistant. |
| Avertizări către | – | La fel, pentru alertele de verificat. Gol = notificări în Home Assistant. |
| Informații către | – | Ce a făcut casa singură: a început sau s-a încheiat sezonul de încălzire, a început o vacanță planificată, preîncălzirea dinaintea întoarcerii, vacanța automată, modul oaspeți oprit singur. Gol = fără anunț. |
| Anunță când o alertă se încheie | pornit | Un mesaj când un dispozitiv funcționează din nou, o fereastră s-a închis sau o baterie a fost schimbată. |
| Amintește când pauza durează mai mult de | 12 h | O avertizare când încălzirea rămâne în pauză atât timp, apoi o dată pe zi. 0 = niciodată. |
| Ore de liniște de la / până la | – | În acest interval doar alertele importante; celelalte se trimit la sfârșitul lui, dacă mai sunt valabile. |
| Alertă când o fereastră e deschisă mai mult de | 30 min | Cât timp încălzirea e necesară. |
| Alertă când un dispozitiv e indisponibil mai mult de | 15 min | Termostat sau senzor. |
| Baterie descărcată sub | 20 % | Dispozitivele camerei (TRV, senzori). |
| Verifică comenzile | pornit | După 2 minute verifică dacă dispozitivul a acceptat comanda, reîncearcă o dată, apoi dă alertă. |
| Alertă când o cameră rămâne mai rece cu | 0 (oprit) | Alertă când o cameră rămâne cu atâtea grade sub țintă în timp ce altele sunt calde (robinet blocat, fereastră deschisă). Apare doar cu mai multe camere. |

Lista alertelor: [capitolul 9](09-ferestre-manual-siguranta.ro.md#alertele).
