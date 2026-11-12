# 8. Sursa de căldură și energia

*[English](08-heat-source-and-energy.md) · [Cuprins](README.ro.md)*

## E nevoie de *Sursa de căldură*?

Depinde cine pornește centrala:

| Situația | *Sursa de căldură* |
| --- | --- |
| Un **Generic Thermostat** pornește centrala (prin releul lui) | **Niciuna.** GT pornește deja centrala; cu GT pe zona *Whole house* formularul nu oferă o sursă de căldură. |
| Un **releu** al camerei pornește direct centrala sau un radiator | **Niciuna.** Releul e deja comandat de integrare; cu un releu pe zona *Whole house* formularul nu oferă o sursă de căldură. |
| **TRV-uri** sau robinete de zonă, iar centrala are un releu sau un termostat în Home Assistant | **Se alege centrala** (sau releul ei). Integrarea o pornește când camerele cer căldură. |
| TRV-uri, iar centrala e pornită de un termostat care **nu e în Home Assistant** | Nu se poate alege nimic. Merge, dar învățarea nu e sigură ([capitolul 7](07-anticipare-si-invatare.ro.md#când-nu-se-recomandă)). |

De ce contează: un TRV doar deschide sau închide robinetul caloriferului. Dacă
centrala nu pornește, caloriferul rămâne rece.

Alegerea completă a configurării, pentru fiecare tip de locuință, e în
[capitolul 2](02-instalare-si-casa.ro.md#ce-configurare-aleg-pentru-casa-mea).
Un dispozitiv folosit de zona *Întreaga casă* sau de o cameră nu poate fi și
*Sursă de căldură* (un dispozitiv, un singur rol).

**Un termostat (Generic Thermostat sau altul) sau un releu pe toată casa, plus
camere cu TRV-uri.** Centrala merge atunci doar când zona întregii case cere
căldură (după propriul senzor). O cameră cu TRV care are nevoie de căldură cât
acel senzor e cald rămâne rece: integrarea nu poate porni centrala pentru ea.
Soluția: releul centralei ca *Sursă de căldură* în loc de pe toată casa (cu un
termostat care pornește și el centrala, un releu legat în paralel cu el), sau
termostatul folosit ca *Sursă de căldură* (cu *Pornește și oprește sursa prin temperatura ei*) în loc de pe toată casa.

## Cum comandă integrarea sursa de căldură

Sursa poate fi un `switch`, un `input_boolean` sau un `climate` (de exemplu
termostatul centralei). Un `switch` sau un `input_boolean` e pornit și oprit.

Un `climate` (un termostat Hive, Nest, Tado sau Netatmo, un Generic Thermostat)
pornește centrala doar după ținta și senzorul lui: trecut pe `heat` cu o țintă
mică, nu o pornește. De aceea, cu **Pornește și oprește sursa prin temperatura
ei** (pornit implicit) rămâne pe încălzire și primește:

- ca să **pornească**: *Temperatura maximă* a casei (implicit 25 °C), nu peste
  maximul termostatului;
- ca să se **oprească**: *Temperatura sursei în repaus*, implicit temperatura de
  *Antiîngheț* a casei (7 °C), nu sub minimul lui. La antiîngheț nu încălzește
  între timp după senzorul lui, dar protejează casa la îngheț dacă Home
  Assistant se oprește.

**Temperatura sursei în repaus** (opțională, doar cu *Pornește și oprește sursa prin temperatura ei*): o valoare mai mare,
de exemplu 17,5 °C, îl lasă pe termostat să țină zona lui la acea temperatură,
după senzorul lui, cât nicio cameră nu cere căldură. Util când încălzește și
calorifere **fără TRV** (un termostat pe hol, TRV-uri doar în unele camere):
acele camere sunt ținute cam la acea temperatură, iar o cameră cu TRV care cere
căldură primește în continuare maximul. Trebuie să fie sub maximul casei. Nu
ridicați pentru asta *Antiînghețul* casei: e și temperatura modului Oprit și a
unei ferestre deschise, și cea mai mică valoare pe care o poate avea un nivel.

O țintă pusă manual pe el e readusă. Fără *Pornește și oprește sursa prin temperatura ei*, sau pentru un termostat fără
temperatură țintă, i se schimbă doar modul: `heat` (sau `auto`, dacă nu are
`heat`) la pornire și `off` la oprire; atunci încălzește după ținta lui, care
trebuie să fie peste senzorul lui.

> **Exemplu (un Hive pe hol, TRV-uri în camere):** livingul cere căldură, Hive
> primește 25 °C și pornește centrala deși pe hol sunt 20 °C; când livingul s-a
> încălzit primește 7 °C și centrala se oprește.

**Pornește** sursa când:

- cer căldură cel puțin *Camere necesare pentru pornirea sursei* camere
  (implicit 1, adică oricare), sau
- cu o *Cameră de referință* setată, când cere căldură acea cameră (celelalte
  doar își deschid sau închid robinetele), sau
- o cameră e în **antiîngheț** și are nevoie de căldură. Antiînghețul pornește
  sursa singur, fără camerele necesare, fără camera de referință și chiar în
  pauză.

**Oprește** sursa când nu mai e îndeplinită condiția.

**Timpii minimi**: *Timp minim pornită* și *Timp minim oprită* (implicit 0,
adică fără așteptare: sursa urmează imediat cererea de căldură). Cu o valoare
mai mare protejează centrala de porniri și opriri dese, pentru centralele fără
protecție proprie la cicluri scurte. Se respectă și peste o repornire a Home
Assistant. Când un timp minim se termină, integrarea verifică imediat din nou.

> [!WARNING]
> **TRV-uri pe toate caloriferele: bypass sau un calorifer fără TRV.**
>
> Când ultima cameră nu mai cere căldură (a ajuns la țintă), TRV-urile ei
> primesc ținta și decid singure: multe se închid complet (senzorul lor e lângă
> caloriferul cald), unele lasă robinetul puțin deschis. Sursa de căldură merge
> până la capătul timpului minim pornită, dacă e setat unul, iar căldura rămasă
> în ea și în țevi tot are nevoie pe unde să treacă. Instalația ar trebui să
> lase apa să circule, ca și cu TRV-uri mecanice obișnuite: un bypass automat,
> o centrală cu bypass intern sau un calorifer fără TRV (de obicei în baie).
> Fără așa ceva, se alege un *Timp minim pornită* mic sau 0 (implicit) și se
> poate folosi *Ține deschis ultimul TRV* (mai jos).

**Ține deschis ultimul TRV** (oprit implicit; doar cu o *Sursă de căldură*):
când nu mai cere căldură nicio cameră, TRV-urile ultimei camere care a cerut
rămân deschise, ca restul de căldură din sursă și din țevi să aibă pe unde
trece, ca printr-un bypass, iar robinetul să nu se mai miște noaptea (mai puțin
zgomot, mai puțină baterie). Când se opresc mai multe camere deodată, e aleasă
cea mai departe sub țintă.

- TRV-urile primesc temperatura maximă a camerei (în limita maximului
  TRV-ului); cele comandate *Pornit / oprit* rămân pornite. Și cele comandate
  prin *Preset* primesc acea temperatură, ca la mișcarea robinetelor, iar
  apoi din nou presetul lor.
- Între timp camera nu cere căldură: sursa rămâne oprită. Ținta ei rămâne cea
  a regulii ei (cardul o arată, cu motivul *Ținut deschis pentru sursa de
  căldură*).
- Se termină când altă cameră cere căldură, când camera e preluată de o regulă
  mai puternică (fereastră, modificare manuală, pauză, modul Oprit sau Vară,
  în afara sezonului, cald afară, mișcarea robinetelor) sau când camera însăși
  e destul de rece ca să ceară căldură (ținta minus histerezisul); TRV-urile
  primesc atunci din nou ținta.
- Ce accepți când o pornești: camera se poate încălzi peste țintă (cu căldura
  rămasă în instalație), iar învățarea ei sare peste timpul cât e ținută
  deschisă (un calorifer deschis ar arăta ca o cameră care se răcește încet).
- Camerele cu relee, cu Generic Thermostat sau care nu se încălzesc de la
  sursa casei nu sunt ținute deschise niciodată.

**Se încălzește la ocazie** (pe cameră, oprit implicit; doar pentru o cameră
cu TRV-uri sau relee care se încălzește de la *Sursa de căldură*, nu pentru un
Generic Thermostat, care își decide singur releul): cât centrala merge pentru
alte camere, o cameră care e puțin sub țintă, în histerezisul ei (implicit
0,3 °C), deci încă nu cere căldură, își deschide TRV-urile sau releul și se
încălzește până la țintă. Ar cere curând și ar porni din nou centrala; așa
centrala pornește mai rar.

- TRV-urile primesc temperatura maximă a camerei, ca la ținerea deschisă;
  releul e pornit. Ținta camerei rămâne cea a regulii ei (cardul arată motivul
  *Încălzită la ocazie: centrala merge deja pentru alte camere*).
- Între timp camera nu cere căldură: nu pornește centrala, nu o ține pornită
  și nu se numără la *Camere necesare*.
- Se termină la țintă, când se oprește centrala sau când camera e preluată de
  o regulă mai puternică (fereastră, modificare manuală, pauză, modul Oprit sau
  Vară, cald afară, oprirea optimă). Un TRV care încă încălzește în histerezis
  după aceea nu pornește din nou centrala; sub histerezis, camera cere căldură
  ca de obicei.
- Cu un circuit, doar cât acel circuit e deja deschis (nu se pornește o pompă
  pentru câteva zecimi de grad). Învățarea ei sare peste acest timp, ca la
  ținerea deschisă.
- Cu *Ține deschis ultimul TRV*: camera ținută deschisă nu se încălzește la
  ocazie. Când altă cameră cere căldură și camera ținută deschisă e în
  histerezis, trece direct la încălzirea la ocazie: TRV-urile ei rămân
  deschise, fără să primească ținta între timp.

**În pauză** integrarea nu comandă sursa, cu o singură excepție: o pornește
pentru antiîngheț și o oprește din nou când nu mai e nevoie (și după o
repornire în timpul pauzei).

**Exemplu cu camere necesare.** Patru camere cu TRV și *Camere necesare*
2. Doar dormitorul cere căldură: centrala nu pornește, iar cardul arată în
dormitor *Nu încălzește: așteaptă alte camere: 1 din 2 cer căldură*. Când cere
și sufrageria, centrala pornește.

## Circuite de încălzire

Unele case au mai multe circuite de încălzire pe aceeași centrală, fiecare cu
pompa sau ventilul lui de zonă: încălzire în pardoseală și calorifere, parterul
și etajul. Centrala nu trebuie să meargă cât toate circuitele sunt închise.

1. În opțiunile casei, la sursa de căldură, alege **Releele circuitelor**
   (`switch` sau `input_boolean`), câte unul pe circuit. Câmpul apare doar cu o
   *Sursă de căldură*.
2. La fiecare cameră pe centrală, alege-i **Circuitul** (pasul de după
   dispozitive; apare doar când casa are relee de circuit). O cameră fără
   circuit merge ca înainte.

Ce face integrarea:

- Când o cameră cere căldură, releul circuitului ei e pornit **întâi**, apoi
  centrala.
- Când nicio cameră a unui circuit nu mai are nevoie de el, centrala se oprește
  **întâi** (după timpul ei minim pornit, dacă e setat), apoi releul. Cât altă
  cameră ține centrala pornită, un circuit care nu mai e necesar e închis
  imediat.
- Centrala nu e pornită pentru o cameră al cărei circuit e oprit (indisponibil
  sau oprit de mână): cardul spune *circuitul ei (…) e oprit*.
- O cameră secundară nu își deschide circuitul; încălzește cât circuitul ei e
  deschis pentru altă cameră.
- Antiînghețul deschide circuitul și pornește centrala.
- *Ține deschis ultimul TRV* ține deschise TRV-urile acelei camere, dar
  circuitul ei se închide după ce se oprește centrala, ca o pompă să nu meargă
  toată noaptea.
- O cameră care așteaptă *Camere necesare* sau *Camera de referință* nu își
  deschide circuitul: circuitele se deschid doar când urmează să pornească
  centrala.
- Fără întârzieri: releul nu așteaptă pornirea pompei sau deschiderea
  ventilului. Un ventil de zonă cu contact de capăt care pornește singur
  centrala nu are nevoie de circuit aici.

## Când „încălzește” o cameră

Pentru învățare și pentru timpul de încălzire, o cameră **încălzește doar cât
merge sursa ei**:

- Generic Thermostat: când spune că încălzește (`hvac_action`);
- releu sau termostat pornit / oprit: când e pornit;
- cu *Sursa de căldură* setată: în plus, doar cât merge și sursa (nu și pentru o
  cameră cu *Se încălzește de la sursa de căldură a casei* oprit).

**Camere cu încălzirea lor.** Într-o casă cu *Sursă de căldură*, o cameră
încălzită altfel (radiator electric, pompă de căldură, aer condiționat) are *Se
încălzește de la sursa de căldură a casei* oprit, la pasul dispozitivelor. Atunci
nu pornește centrala (nici la *Camere necesare*, nici pentru antiîngheț), nu
poate fi *Cameră de referință* și încălzește cât merge propriul dispozitiv.

**Camere secundare.** O cameră pe centrală poate fi făcută secundară: la pasul de
după dispozitivele ei, *Poate porni sursa de căldură a casei* oprit (implicit
pornit; apare doar când camera se încălzește de la sursa casei). O cameră
secundară nu pornește niciodată centrala pentru ea, nu se numără la *Camere
necesare*, nu poate fi *Cameră de referință* și nu e camera rece din *Alertă
când o cameră rămâne mai rece cu*; TRV-urile, vanele sau releele ei se deschid totuși cât e sub țintă,
deci primește căldură doar cât centrala merge pentru altă cameră. Potrivit
pentru camere care nu trebuie să fie reci, dar nici calde la o oră anume:
balcoane închise, camera de oaspeți, hol, debara. Într-o zi blândă centrala
poate merge puțin, așa că o cameră secundară poate rămâne ore întregi sub țintă.
Antiînghețul pornește totuși centrala pentru ea, din motive de siguranță.
Învățarea și timpul ei de încălzire se numără doar cât merge centrala, ca la
orice cameră de pe centrală. O cameră secundară care cere căldură nu oprește
*Ține deschis ultimul TRV*.

O cameră care cere căldură în timp ce sursa așteaptă alte camere se răcește, iar
asta se învață ca pierdere de căldură. Cât timp starea sursei e necunoscută, nu se învață
nimic.

## Când nu încălzește o cameră sub țintă

Cardul spune de ce, iar senzorul *Decizie* are atributul `no_heat_reason`:

| Motiv | Ce înseamnă |
| --- | --- |
| camera e în toleranța termostatului | e foarte puțin sub țintă, termostatul încă așteaptă |
| în histerezisul de … | releul așteaptă să coboare sub țintă − histerezis |
| oprită mai devreme: căldura deja dată duce camera la ~… | *Folosește inerția învățată*: camera se mai încălzește singură până acolo |
| releul așteaptă timpul minim pornit / oprit | protecția releului |
| sursa de căldură așteaptă timpul minim pornit / oprit | protecția centralei |
| așteaptă alte camere: X din Y cer căldură | *Camere necesare* |
| cameră secundară: primește căldură când altă cameră pornește sursa de căldură | *Poate porni sursa de căldură a casei* oprit |
| circuitul ei (…) e oprit: pompa sau ventilul nu merge | releul circuitului camerei e oprit sau indisponibil, vezi [Circuite de încălzire](#circuite-de-încălzire) |
| așteaptă camera de referință … | *Cameră de referință* |
| sursa de căldură e oprită / starea ei e necunoscută | centrala nu merge sau nu se știe |
| termostatul e oprit | termostatul camerei e pe `off` |

## Alerte legate de sursă

- **Sursa de căldură indisponibilă** mai mult de *Alertă când un dispozitiv e
  indisponibil mai mult de* (implicit 15 minute): atunci nu se încălzește
  deloc, nici pentru antiîngheț.
- **Alertă când o cameră rămâne mai rece cu** (la opțiunile *Alerte*, implicit
  0 = oprit, apare doar cu mai multe camere): o cameră rămâne cu atâtea grade sub
  țintă în timp ce altele sunt calde (robinet blocat, fereastră uitată deschisă).

## Tariful dinamic

Cu un *Senzor preț energie* (de exemplu Nord Pool, Tibber):

- la **preț mare** (*Preț mare de la* sau peste) se adaugă *Ajustare la preț
  mare* (implicit −1 °C): casa e puțin mai rece cât e scump;
- la **preț mic** (*Preț mic până la* sau sub) se adaugă *Ajustare la preț mic*
  (implicit +0,5 °C): casa se încălzește puțin mai mult cât e ieftin.

Pragurile sunt în unitatea senzorului (de exemplu lei/kWh). Dacă un prag e
gol, ajustarea lui nu se folosește.

**Exemplu** (valori alese): preț mare de la 1,20, ajustarea implicită −1 °C,
`home` 21 °C. Când prețul e 1,35, ținta e 21 − 1 = 20 °C.

## Surplusul fotovoltaic

Cu un *Senzor surplus fotovoltaic* (puterea trimisă în rețea, în W): cât
surplusul e cel puțin *Surplus de la* (implicit 1000 W), se adaugă *Ajustare cu
surplus* (implicit +0,5 °C). Util doar cu încălzire electrică sau pompă de
căldură: energia proprie e folosită în loc să fie vândută ieftin.

Ajustările de energie se adună cu celelalte (compensare, câștig solar), suma e
limitată la ±3 °C și nu se aplică niciodată unui antiîngheț
([capitolul 6](06-vreme.ro.md#cum-se-adună-ajustările)).

## Timpul de încălzire

- **Timp de încălzire** al fiecărei camere: cât timp a încălzit camera (cât a
  mers sursa ei).
- **Timp de încălzire** al casei: cât timp a mers sursa de căldură; fără sursă,
  cât timp a încălzit cel puțin o cameră.
- **Cerere de căldură** (senzor binar) al casei: dacă se cere acum căldură; al
  camerei: dacă cere camera, cu atributul `heating` (dacă sursa ei merge).

Senzorii de timp sunt totaluri crescătoare (ore), deci Home Assistant le
păstrează în statisticile pe termen lung. Cardul arată timpul pe zi, săptămână
sau lună ([capitolul 10](10-card.ro.md)).
