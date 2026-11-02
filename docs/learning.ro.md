# Cum învață Smart Heating Control (modelul termic al camerei)

*[English](learning.md)*

Documentul explică cum învață fiecare cameră cum se încălzește, cum pierde
căldură și cât de încet reacționează încălzirea ei (inerția termică), cum se
calculează numerele și cum sunt folosite pentru **pornirea anticipată**,
**oprirea anticipată** și **timpul până la țintă** afișat pe card. Fiecare
număr din exemple este fie calculat în text, fie precizat ca ipoteză a
exemplului.

Intern toate calculele se fac în °C; la o casă în °F se convertește doar
afișarea (1 °C = 1,8 °F).

- [1. De ce învățare](#1-de-ce-învățare)
- [2. Modelul unei camere](#2-modelul-unei-camere)
- [3. Ce se măsoară: intervale de 30 de minute](#3-ce-se-măsoară-intervale-de-30-de-minute)
- [4. Cum se calculează încălzirea și pierderea](#4-cum-se-calculează-încălzirea-și-pierderea)
- [5. Cum se învață inerția](#5-cum-se-învață-inerția)
- [6. Când se folosește modelul învățat](#6-când-se-folosește-modelul-învățat)
- [7. Folosirea modelului](#7-folosirea-modelului)
- [8. O casă fără temperatură de afară](#8-o-casă-fără-temperatură-de-afară)
- [9. Simulări fictive](#9-simulări-fictive)
- [10. Limite](#10-limite)
- [11. Unde se vede](#11-unde-se-vede)

---

## 1. De ce învățare

Ca să fie 21 °C în cameră la 07:00, încălzirea trebuie să pornească mai
devreme. Cât de devreme depinde de cameră: sursa de căldură, caloriferele sau
încălzirea în pardoseală, izolația, temperatura de afară. În loc să ceară
aceste valori, fiecare cameră își măsoară propriul comportament și învață din
el. Nu trebuie setat nimic: și inerția (o pardoseală lentă sau calorifere
rapide) se învață, nu se alege în configurare.

---

## 2. Modelul unei camere

Camera este tratată ca o singură masă termică ce primește căldură de la
încălzire și pierde căldură spre exterior, proporțional cu cât este mai caldă
decât afară:

```
creștere pe oră = h × q − k × (cameră − afară)
```

| Număr | Nume în atribute | Semnificație |
|---|---|---|
| h | `heating_per_hour` | câte °C pe oră adaugă încălzirea când dă toată căldura |
| k | `loss_per_hour` | ce parte din diferența interior / exterior se pierde pe oră |
| q | `heat_reaching_now` | cât din încălzire ajunge acum în cameră, de la 0 (nimic) la 1 (tot) |
| τ | `inertia_minutes` | cât de încet urmează q încălzirea (inerția termică) |

**Inerția.** După pornirea încălzirii se încălzesc întâi centrala, apa și
caloriferele (sau șapa unei încălziri în pardoseală); după oprire, ele mai dau
căldură o vreme. q urmează încălzirea cu întârzierea τ:

```
q se apropie de 1 (încălzire pornită) sau de 0 (oprită) cu (țintă − q) × minute ÷ τ
```

deci după τ minute q a parcurs circa 63 % din drum (1 − e⁻¹), după 3 × τ circa
95 %. τ = 0 înseamnă fără inerție: q este 1 imediat ce încălzirea merge.

**Exemplu** (valori presupuse pentru exemplu): h = 2 °C/h, k = 0,05 pe oră,
τ = 30 de minute. Camera la 19 °C, afară 5 °C, încălzirea ajunsă complet
(q = 1):

- pierdere: 0,05 × (19 − 5) = **0,7 °C/h**;
- creștere: 2 × 1 − 0,7 = **1,3 °C/h**;
- fără încălzire (q = 0) camera scade cu 0,7 °C/h.

Pierderea crește cu diferența: la 21 °C și 0 °C afară este 0,05 × 21 =
1,05 °C/h. Cu cât e mai frig afară, cu atât încălzirii îi rămâne mai puțin
pentru a ridica temperatura, deci fiecare grad durează mai mult: la 20 °C în
cameră, 60 ÷ (2 − 0,05 × 20) = **60 de minute pe grad** la 0 °C afară,
60 ÷ (2 − 0,05 × 10) = **40 de minute** la 10 °C.

---

## 3. Ce se măsoară: intervale de 30 de minute

Camera este urmărită tot timpul, cu sau fără încălzire. Fiecare **interval de
30 de minute** dă o măsurătoare:

- cât a crescut sau a scăzut camera, pe oră;
- media lui q pe interval (pentru fiecare τ candidat, secțiunea 5);
- media diferenței (cameră − afară) pe interval.

De ce 30 de minute: destul de lung încât pasul senzorului (de obicei 0,1 °C)
să fie mic față de schimbare, destul de scurt încât să se vadă un ciclu de
încălzire.

**Un interval nu se folosește** când:

- un **senzor de fereastră sau ușă** al camerei (sau unul legat) a fost
  deschis;
- **starea sursei de căldură** a fost necunoscută;
- rula **exercițiul robinetelor**;
- casa are temperatură de afară (senzor sau entitate meteo), dar aceasta a fost
  **necunoscută**;
- citirile au fost la mai mult de **20 de minute** distanță (intervalul începe
  din nou);
- nu este **sezonul rece** (modul Oprit sau Vară, ori în afara sezonului de
  încălzire).

„Încălzire” înseamnă ce însemna și înainte: camera cere căldură **și sursa ei
de căldură merge** (`hvac_action` la Generic Thermostat, releul sau
termostatul pornit / oprit pornit, *Sursa de căldură* a casei dacă este
setată).

**Exemplu** (cu camera din secțiunea 2): 30 de minute cu încălzirea pornită,
q de la 0,5 la 0,82 (cu τ = 30: 1 − 0,5 × e⁻¹ = 0,82; media 0,68), camera la
circa 19 °C, afară 5 °C. Creștere: 2 × 0,68 − 0,05 × 14 = 1,36 − 0,7 =
0,66 °C/h, deci 0,33 °C în cele 30 de minute. Integrarea vede cele 0,33 °C,
pe 0,68 și pe 14; trebuie să găsească h și k.

Nu se păstrează nimic pe interval: doar sumele metodei celor mai mici pătrate
(secțiunea 4), deci memoria nu crește, iar o repornire păstrează tot ce s-a
învățat (intervalul în curs se pierde).

---

## 4. Cum se calculează încălzirea și pierderea

Fiecare interval este o ecuație:

```
creșterea măsurată pe oră = h × (q mediu) − k × (cameră − afară, medie)
```

h și k sunt numerele pentru care ecuațiile tuturor intervalelor sunt **cât mai
aproape** de ce s-a măsurat: suma diferențelor la pătrat este cea mai mică
(**metoda celor mai mici pătrate**). Două necunoscute dau două ecuații,
rezolvate după fiecare interval:

```
h × Σ q²     − k × Σ q·d  = Σ q·r
h × Σ q·d    − k × Σ d²   = Σ d·r
```

(q: q mediu, d: media cameră − afară, r: creșterea pe oră a fiecărui interval.)

**Intervalele mai vechi contează mai puțin.** Un interval își păstrează
ponderea o săptămână, apoi contează pe jumătate, după două săptămâni un sfert
(timp de înjumătățire **7 zile**). Astfel modelul urmează o cameră care se
schimbă (o nouă curbă de temperatură, calorifere noi, anotimpul) fără să
trebuiască resetat.

**Intervalele departe de celelalte contează mai puțin.** O ușă lăsată deschisă
fără senzor, gătitul, soarele puternic: camera face altceva decât așteaptă
modelul. După 10 intervale, fiecare interval nou se compară cu ce spunea
modelul înainte de a învăța din el. Diferența obișnuită este media ponderată a
acestor diferențe; un interval aflat la mai mult de **2,5 ori** diferența
obișnuită contează cu o pondere proporțional mai mică (la de 5 ori diferența
obișnuită: pe jumătate). Un astfel de interval contează totuși puțin, deci
când camera s-a schimbat cu adevărat modelul o urmează.

**O tragere foarte mică spre valoarea implicită** (1 °C/h, fără pierdere), cât
circa 1 % dintr-un interval, împiedică primele intervale să dea numere
aberante; după o zi nu mai contează.

**Valori imposibile:**

- o **pierdere negativă** (camera s-ar încălzi singură): pierderea devine 0 și
  se potrivește doar încălzirea;
- o **încălzire de zero sau mai puțin**: acel candidat nu se folosește.

---

## 5. Cum se învață inerția

τ nu se poate calcula ca h și k (q depinde de el într-un mod curb). Integrarea
învață **zece candidați în același timp**, fiecare cu τ-ul lui:

```
0, 10, 20, 30, 45, 60, 90, 120, 180, 240 de minute
```

Pentru fiecare candidat q se urmărește cu τ-ul lui, iar h și k se potrivesc ca
în secțiunea 4. Înainte de a învăța dintr-un interval, fiecare candidat îl
**prezice**; se folosește candidatul cu cea mai mică eroare pătratică medie de
predicție (uitată la fel ca intervalele). Diagnosticul îi arată pe toți zece,
cu erorile lor.

**De ce contează** (camera din secțiunea 2, 18 → 21 °C, afară 0 °C, încălzirea
pornește la rece, q = 0):

| | minute |
|---|---|
| τ = 30 de minute | **231** |
| aceeași cameră fără inerție (τ = 0) | 176 |

Fără inerție pornirea ar fi cu 55 de minute prea târzie. După o oprire efectul
este invers: camera din secțiunea 2 la 21 °C (q = 1, tocmai a încălzit),
confort până la 20,5 °C, afară 0 °C, are nevoie de **82 de minute** ca să scadă
la confort cu τ = 30, față de 29 de minute fără inerție: oprirea anticipată
poate începe cu aproape o oră mai devreme.

---

## 6. Când se folosește modelul învățat

Modelul se folosește după ce a văzut **8 intervale cu încălzirea pornită** (q
mediu cel puțin 0,5) **și 8 fără** (q mediu cel mult 0,2), adică 4 ore din
fiecare. Sunt necesare amândouă: doar cu încălzire, încălzirea și pierderea nu
se pot deosebi. Aceste numărători se uită la fel ca intervalele.

Până atunci se folosește valoarea implicită: **1 °C pe oră (60 de minute pe
grad), fără pierdere, fără inerție**, iar oprirea anticipată nu se calculează
(se folosește *Oprirea anticipată maximă* a camerei ca atare). Într-o cameră
locuită cele 4 + 4 ore se adună de obicei în prima zi.

---

## 7. Folosirea modelului

Toate predicțiile sunt o **simulare minut cu minut** cu modelul învățat,
pornind de la temperatura camerei și q de acum, pentru cel mult 24 de ore.

### Pornirea anticipată

Pentru următoarea schimbare programată spre un nivel mai cald (de exemplu
*Somn* 18 °C → *Acasă* 21 °C la 07:00):

1. simularea rulează cu încălzirea pornită până când camera ajunge la nivelul
   presetării următoare. Exemplu: camera din secțiunea 2 la 18 °C, prognoză
   medie de 5 °C: **186 de minute**; la −5 °C: **303 minute**;
2. temperatura de afară este **media prognozei** între pornire și 07:00 (cu o
   entitate meteo care are prognoză orară; altfel valoarea măsurată). Pornirea
   depinde de această temperatură, iar temperatura de pornire, deci se
   calculează de **3 ori**, de fiecare dată din perioada găsită înainte;
3. pornirea nu este **niciodată mai devreme** decât *Pornirea anticipată
   maximă* a camerei. Cu un maxim de 120 de minute pornirea este la 07:00 − 120
   de minute = 05:00, altfel la 07:00 − 186 de minute = 03:54;
4. odată pornită continuă până la 07:00, chiar dacă se încălzește camera mai
   devreme.

**Deja încălzește.** Se folosește q de acum: o cameră cu caloriferele deja
calde are nevoie de mai puțin. Exemplu: camera din secțiunea 2, 18 → 21 °C la
0 °C, cu q = 0,5: **203 minute** în loc de 231.

### Timpul până la țintă

Cât timp o cameră este sub țintă, cardul arată timpul până la țintă
(*~35 min*), cu aceeași simulare, temperatura de afară de acum și q de acum.

### Oprirea anticipată

Înainte de o schimbare spre un nivel mai rece, încălzirea se oprește mai
devreme, atât cât camera rămâne în **confortul** nivelului curent: nivel −
toleranță. Exemplu: *Acasă* 21 °C, toleranță 0,5 °C → confort până la 20,5 °C.
Simularea rulează **fără încălzire** până când camera ajunge la confort;
inerția contează (caloriferele încă dau căldură). Cu camera din secțiunea 2
imediat după încălzire (q = 1): **82 de minute** la 0 °C afară, **162 de
minute** la 10 °C.

Oprirea nu este niciodată mai lungă decât maximul *Oprire anticipată* al
camerei. Dacă în timpul opririi camera se răcește sub confort, oprirea se
anulează și nivelul curent revine până la schimbare. Cu prognoză orară se
folosește media prognozei pe perioada opririi, în 3 treceri ca la pornire. În
timpul unei opriri, senzorul de decizie arată temperatura așteptată la
schimbare, din aceeași simulare.

---

## 8. O casă fără temperatură de afară

Fără senzor de exterior și fără entitate meteo, pierderea nu poate depinde de
temperatura de afară: se învață ca **un număr constant de °C pe oră**
(`constant_loss: true`, `loss_per_hour` în °C pe oră). Este pierderea medie a
ultimelor săptămâni; zilele mai reci nu se văd. Oprirea anticipată are nevoie
de o temperatură de afară și nu se face.

Când se adaugă sau se elimină o sursă de temperatură de afară, modelul se
învață din nou de la început, pentru că se schimbă sensul pierderii.

---

## 9. Simulări fictive

Simulările de mai jos folosesc **camere fictive**: numerele sunt alese să fie
plauzibile, nu sunt măsurători.

| Cameră | h (°C/h) | k (pe oră) | τ (minute) |
|---|---|---|---|
| Apartament izolat | 1,6 | 0,035 | 20 |
| Casă obișnuită | 2,8 | 0,07 | 30 |
| Casă veche, slab izolată | 4,5 | 0,12 | 30 |
| Încălzire în pardoseală | 1,6 | 0,04 | 180 |

Ipoteze: 40 de zile; temperatura zilnică de afară aleatoare între −5 și
10 °C, cu ±3 °C între zi și noapte; un termostat la 21 °C între 06:00 și 23:00
și 17 °C noaptea, ±0,3 °C; senzorul citit la 5 minute, rotunjit la 0,1 °C;
perturbări aleatoare ale camerei (abatere standard 0,15 °C/h în fiecare
minut). Din ziua 8, în fiecare dimineață la 06:00 se prezice timpul până la
21 °C cu temperatura medie de afară a încălzirii (o prognoză perfectă) și se
compară cu cel real.

| Cameră | model folosit după | h / k / τ învățate | eroare: medie / cea mai mare (minute) |
|---|---|---|---|
| Apartament izolat | 0,4 zile | 1,59 / 0,035 / 20 | 2 / 8 |
| Casă obișnuită | 0,5 zile | 2,78 / 0,070 / 30 | 2 / 5 |
| Casă veche | 0,8 zile | 3,76 / 0,100 / 20 | 9 / 16 |
| Încălzire în pardoseală | 0,7 zile | 1,60 / 0,040 / 180 | 2 / 9 |

La casa veche h și k au ieșit mai mici în aceeași proporție (3,76 ÷ 0,100 ≈
4,5 ÷ 0,12): camera vede rar diferențele mari care le-ar deosebi, iar
predicțiile rămân apropiate.

**Cu curbă de temperatură** (centrala dă mai multă căldură când e mai frig:
aici h este cu 3 % mai mare pentru fiecare °C sub 5 °C afară), modelul, care
are un singur h, este mai puțin exact:

| Cameră, cu curbă de temperatură | eroare: medie / cea mai mare (minute) |
|---|---|
| Apartament izolat | 28 / 56 |
| Casă obișnuită | 22 / 52 |
| Casă veche | 16 / 38 |
| Încălzire în pardoseală | 42 / 122 |

---

## 10. Limite

- **O curbă de temperatură** la centrală schimbă puterea încălzirii cu
  temperatura de afară; modelul are un singur h, o medie pe ultimele
  săptămâni (secțiunea 9).
- **Diferențele de la o zi la alta nu se învață.** Soarele, oamenii, gătitul
  sau pereții mai reci după o absență lungă schimbă camera; metoda celor mai
  mici pătrate le face media.
- **Robinete termostatice cu o centrală pornită de un termostat care nu este în
  Home Assistant**: integrarea nu poate ști când merge centrala; învățarea nu
  este de încredere, iar pornirea / oprirea anticipată nu sunt recomandate.
- **Așteptările dinainte de pornirea sursei de căldură** (timpii minimi de
  pornire / oprire, *Camere necesare pentru pornirea sursei*, camera de
  referință) nu sunt încălzire: pornirea poate întârzia cu acea așteptare.
- **Învățarea salvată înainte de 2.6** (episoade de încălzire și răcire) nu se
  potrivește noului model și se renunță la ea: după actualizare fiecare cameră
  învață din nou, în circa o zi.

---

## 11. Unde se vede

**`sensor.<cameră>_heating_rate`** – stare: minute pe grad cu încălzirea
complet pornită, la temperatura camerei și cea de afară de acum (`min/°C` sau
`min/°F`). Atribute:

| Atribut | Semnificație |
|---|---|
| `learned` | se folosește modelul învățat (secțiunea 6) |
| `heating_per_hour` | h |
| `loss_per_hour` | k (pe oră sau, cu `constant_loss`, °C pe oră) |
| `constant_loss` | pierderea este constantă (secțiunea 8) |
| `inertia_minutes` | τ |
| `heat_reaching_now` | q acum |
| `error_per_hour` | eroarea obișnuită de predicție a unui interval (°C pe oră) |
| `minutes_per_degree` | minute pe grad la −10 / 0 / 10 / 20 °C (14 / 32 / 50 / 68 °F) afară |
| `hours_heating`, `hours_idle`, `hours_needed` | progresul învățării (secțiunea 6) |

**`sensor.<cameră>_cooling_rate`** – stare: cât de repede scade acum camera
fără încălzire (°C/h, gol până se învață); atribute: `learned`,
`loss_per_hour`, `inertia_minutes`, toleranța opririi anticipate.

**`sensor.<cameră>_decision`** – `next_estimate` (când începe următoarea
pornire / oprire anticipată, cu ce temperatură de afară și dacă este învățată
sau implicită) și `time_to_target`.

**`button.<cameră>_reset_learning`** – uită modelul camerei (și în *Detalii* pe
card, cu un al doilea clic pentru confirmare).

**Card, Detalii** – grupul *Învățare*: *Încălzire învățată* (minute pe grad
acum și inerția, de ex. *45 min/°C acum · inerție 30 min*, sau în timpul
învățării *se învață… 2 din 4 h cu încălzire, 1 din 4 h fără*, cu valoarea
implicită dedesubt) și *Pierdere de căldură învățată* (*scade 0,70 °C/h acum*,
după ce se învață), cu butonul **Resetează**.

**Diagnostic** – `thermal_model` cu toate numerele modelului și cei zece
candidați de inerție.
