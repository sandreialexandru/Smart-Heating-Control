# 8. Sursa de căldură și energia

*[English](08-heat-source-and-energy.md) · [Cuprins](README.ro.md)*

## E nevoie de *Sursa de căldură*?

Depinde cine pornește centrala:

| Situația | *Sursa de căldură* |
| --- | --- |
| Un **Generic Thermostat** pornește centrala (prin releul lui) | **Gol.** GT pornește deja centrala. Releul folosit de GT nu se alege niciodată. |
| Un **releu** al camerei pornește direct centrala sau un radiator | **Gol.** Releul e deja comandat de integrare. |
| **TRV-uri** sau robinete de zonă, iar centrala are un releu sau un termostat în Home Assistant | **Se alege centrala** (sau releul ei). Integrarea o pornește când camerele cer căldură. |
| TRV-uri, iar centrala e pornită de un termostat care **nu e în Home Assistant** | Nu se poate alege nimic. Merge, dar învățarea nu e sigură ([capitolul 7](07-anticipare-si-invatare.ro.md#când-nu-se-recomandă)). |

De ce contează: un TRV doar deschide sau închide robinetul caloriferului. Dacă
centrala nu pornește, caloriferul rămâne rece.

## Cum comandă integrarea sursa de căldură

Sursa poate fi un `switch`, un `input_boolean` sau un `climate` (de exemplu
termostatul centralei). Un `climate` e pornit cu modul `heat` (sau `auto`, dacă
nu are `heat`) și oprit cu `off`.

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
> primesc ținta și se închid, dar sursa de căldură merge până la capătul
> timpului minim pornită, dacă e setat unul. Integrarea nu ține un TRV deschis
> pentru asta: ar încălzi camera peste țintă. Instalația însăși trebuie să
> lase apa să circule, ca și cu TRV-uri mecanice obișnuite: un bypass automat,
> o centrală cu bypass intern sau un calorifer fără TRV (de obicei în baie).
> Fără așa ceva, se alege un *Timp minim pornită* mic sau 0 (implicit), ca
> sursa să se oprească imediat ce nu mai cere nicio cameră.

**În pauză** integrarea nu comandă sursa, cu o singură excepție: o pornește
pentru antiîngheț și o oprește din nou când nu mai e nevoie (și după o
repornire în timpul pauzei).

**Exemplu cu camere necesare.** Patru camere cu TRV și *Camere necesare*
2. Doar dormitorul cere căldură: centrala nu pornește, iar cardul arată în
dormitor *Nu încălzește: așteaptă alte camere: 1 din 2 cer căldură*. Când cere
și sufrageria, centrala pornește.

## Când „încălzește” o cameră

Pentru învățare și pentru timpul de încălzire, o cameră **încălzește doar cât
merge sursa ei**:

- Generic Thermostat: când spune că încălzește (`hvac_action`);
- releu sau termostat pornit / oprit: când e pornit;
- cu *Sursa de căldură* setată: în plus, doar cât merge și sursa.

O cameră care cere căldură în timp ce sursa așteaptă alte camere se răcește, iar
asta se învață ca răcire. Cât timp starea sursei e necunoscută, nu se învață
nimic.

## Când nu încălzește o cameră sub țintă

Cardul spune de ce, iar senzorul *Decizie* are atributul `no_heat_reason`:

| Motiv | Ce înseamnă |
| --- | --- |
| camera e în toleranța termostatului | e foarte puțin sub țintă, termostatul încă așteaptă |
| în histerezisul de … | releul așteaptă să coboare sub țintă − histerezis |
| releul așteaptă timpul minim pornit / oprit | protecția releului |
| sursa de căldură așteaptă timpul minim pornit / oprit | protecția centralei |
| așteaptă alte camere: X din Y cer căldură | *Camere necesare* |
| așteaptă camera de referință … | *Cameră de referință* |
| sursa de căldură e oprită / starea ei e necunoscută | centrala nu merge sau nu se știe |
| termostatul e oprit | termostatul camerei e pe `off` |

## Alerte legate de sursă

- **Sursa de căldură indisponibilă** mai mult de *Alertă când un dispozitiv e
  indisponibil mai mult de* (implicit 15 minute): atunci nu se încălzește
  deloc, nici pentru antiîngheț.
- **Alertă când o cameră rămâne mai rece cu** (implicit 0 = oprit): o cameră
  rămâne cu atâtea grade sub țintă în timp ce altele sunt calde (robinet blocat,
  fereastră uitată deschisă). Utilă doar cu mai multe camere.

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
