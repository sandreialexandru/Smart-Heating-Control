# Cum învață Smart Heating Control (modelul termic al camerei)

*[English](learning.md)*

Documentul explică cum învață fiecare cameră cum se încălzește, cum se
schimbă încălzirea cu temperatura de afară (curba de temperatură), cum pierde
căldură, cât o încălzește soarele și cât de încet reacționează încălzirea ei
(inerția termică), cum se
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
- [10. Soarele](#10-soarele)
- [11. Limite](#11-limite)
- [12. Unde se vede](#12-unde-se-vede)

---

## 1. De ce învățare

Ca să fie 21 °C în cameră la 07:00, încălzirea trebuie să pornească mai
devreme. Cât de devreme depinde de cameră: sursa de căldură, caloriferele sau
încălzirea în pardoseală, izolația, temperatura de afară. În loc să ceară
aceste valori, fiecare cameră își măsoară propriul comportament și învață din
el. Nu trebuie setat nimic: și inerția (o pardoseală lentă sau calorifere
rapide), curba de temperatură a centralei și căldura soarelui se învață, nu se
aleg în configurare.

---

## 2. Modelul unei camere

Camera este tratată ca o singură masă termică ce primește căldură de la
încălzire și pierde căldură spre exterior, proporțional cu cât este mai caldă
decât afară:

```
creștere pe oră = (h − c × afară) × q − k × (cameră − afară) + s × soare
```

| Număr | Nume în atribute | Semnificație |
|---|---|---|
| h | `heating_per_hour` | câte °C pe oră adaugă încălzirea când dă toată căldura, la 0 °C afară |
| c | `weather_curve` | câte °C pe oră în plus adaugă încălzirea pentru fiecare °C mai frig afară (*Curba de temperatură* mai jos) |
| k | `loss_per_hour` | ce parte din diferența interior / exterior se pierde pe oră |
| s | `sun_gain` | câte °C pe oră adaugă soarele la un semnal solar de 1 (secțiunea 10) |
| soare | | semnalul solar de acum, de la 0 (noapte, nori groși) la 1 (soarele la zenit pe cer senin) |
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

**Exemplu** (valori presupuse pentru exemplu): h = 2 °C/h, c = 0 (fără curbă
de temperatură), k = 0,05 pe oră, τ = 30 de minute. Camera la 19 °C, afară 5 °C, încălzirea ajunsă complet
(q = 1):

- pierdere: 0,05 × (19 − 5) = **0,7 °C/h**;
- creștere: 2 × 1 − 0,7 = **1,3 °C/h**;
- fără încălzire (q = 0) camera scade cu 0,7 °C/h.

Pierderea crește cu diferența: la 21 °C și 0 °C afară este 0,05 × 21 =
1,05 °C/h. Cu cât e mai frig afară, cu atât încălzirii îi rămâne mai puțin
pentru a ridica temperatura, deci fiecare grad durează mai mult: la 20 °C în
cameră, 60 ÷ (2 − 0,05 × 20) = **60 de minute pe grad** la 0 °C afară,
60 ÷ (2 − 0,05 × 10) = **40 de minute** la 10 °C.

**Curba de temperatură.** O centrală cu curbă de temperatură (compensare după
exterior) face apa mai caldă când e mai frig afară, deci caloriferele dau mai
multă căldură; o pompă de căldură poate da mai puțin la ger; o centrală cu
temperatura apei fixă sau un radiator electric dă la fel. c învață asta:
pozitiv când încălzirea dă mai mult la frig, negativ când dă mai puțin, 0 când
dă la fel. Exemplu: camera de mai sus cu c = 0,05 °C/h pe °C dă
2 − 0,05 × (−5) = **2,25 °C/h** la −5 °C afară și 2 − 0,05 × 10 = **1,5 °C/h**
la 10 °C. De la 18 la 21 °C, pornind la rece:

| Afară | fără curbă (c = 0) | cu c = 0,05 |
|---|---|---|
| −5 °C | 303 minute | 237 de minute |
| 5 °C | 186 de minute | 224 de minute |
| 10 °C | 156 de minute | 217 minute |

Un model fără curbă ar porni cu o oră prea devreme la −5 °C și cu o oră prea
târziu la 10 °C într-o astfel de casă.

---

## 3. Ce se măsoară: intervale de 30 de minute

Camera este urmărită tot timpul, cu sau fără încălzire. Fiecare **interval de
30 de minute** dă o măsurătoare:

- cât a crescut sau a scăzut camera, pe oră;
- media lui q pe interval (pentru fiecare τ candidat, secțiunea 5);
- media diferenței (cameră − afară) pe interval;
- media lui q × afară pe interval (pentru curba de temperatură);
- media semnalului solar pe interval (secțiunea 10).

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
- casa are entitate meteo, dar norii ei au fost **necunoscuți ziua** (semnalul
  solar e necunoscut; noaptea e oricum 0);
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
pe 0,68 și pe 14; trebuie să găsească h, c și k (și s, din semnalul solar).

Nu se păstrează nimic pe interval: doar sumele metodei celor mai mici pătrate
(secțiunea 4), deci memoria nu crește, iar o repornire păstrează tot ce s-a
învățat (intervalul în curs se pierde).

---

## 4. Cum se calculează încălzirea și pierderea

Fiecare interval este o ecuație:

```
creșterea măsurată pe oră = h × (q mediu) − c × (q × afară, medie) − k × (cameră − afară, medie) + s × (soare, medie)
```

h, c, k și s sunt numerele pentru care ecuațiile tuturor intervalelor sunt
**cât mai aproape** de ce s-a măsurat: suma diferențelor la pătrat este cea mai
mică (**metoda celor mai mici pătrate**). Patru necunoscute dau patru ecuații
(ecuațiile normale), rezolvate după fiecare interval prin eliminare Gauss:

```
h × Σ q²   − c × Σ q·p   − k × Σ q·d   + s × Σ q·S   = Σ q·r
h × Σ q·p  − c × Σ p²    − k × Σ p·d   + s × Σ p·S   = Σ p·r
h × Σ q·d  − c × Σ p·d   − k × Σ d²    + s × Σ d·S   = Σ d·r
h × Σ q·S  − c × Σ p·S   − k × Σ d·S   + s × Σ S²    = Σ S·r
```

(q: q mediu, p: media q × afară, d: media cameră − afară, S: media semnalului
solar, r: creșterea pe oră a fiecărui interval.)

**Intervalele mai vechi contează mai puțin.** Un interval își păstrează
ponderea o săptămână, apoi contează pe jumătate, după două săptămâni un sfert
(timp de înjumătățire **7 zile**). Astfel modelul urmează o cameră care se
schimbă (o nouă curbă de temperatură, calorifere noi, anotimpul) fără să
trebuiască resetat.

**Intervalele departe de celelalte contează mai puțin.** O ușă lăsată deschisă
fără senzor, gătitul, un soare pe care entitatea meteo nu l-a văzut: camera face altceva decât așteaptă
modelul. După 10 intervale, fiecare interval nou se compară cu ce spunea
modelul înainte de a învăța din el. Diferența obișnuită este media ponderată a
acestor diferențe; un interval aflat la mai mult de **2,5 ori** diferența
obișnuită contează cu o pondere proporțional mai mică (la de 5 ori diferența
obișnuită: pe jumătate). Un astfel de interval contează totuși puțin, deci
când camera s-a schimbat cu adevărat modelul o urmează.

**O tragere foarte mică spre valoarea implicită** (1 °C/h, fără curbă, fără
pierdere, fără soare), cât
circa 1 % dintr-un interval, împiedică primele intervale să dea numere
aberante; după o zi nu mai contează.

**Valori imposibile:**

- o **pierdere negativă** (camera s-ar încălzi singură): pierderea devine 0 și
  restul se potrivește din nou;
- o **curbă de temperatură care n-ar mai lăsa încălzire** (h − c × afară zero
  sau mai puțin) la −20 °C sau la 20 °C afară, intervalul unui sezon de
  încălzire: curba devine 0 și restul se potrivește din nou;
- un **câștig solar negativ** (soarele ar răci camera): soarele devine 0 și
  restul se potrivește din nou; soarele e lăsat deoparte și cât timp nu se
  vede clar (secțiunea 10);
- o **încălzire de zero sau mai puțin**: acel candidat nu se folosește.

**Când se învață curba.** Curba se poate deosebi de încălzire doar dacă
camera a încălzit la temperaturi de afară diferite. Se folosește după ce
temperaturile de afară ale intervalelor cu încălzire au o abatere standard de
cel puțin **1 °C** (de exemplu o zi și o noapte la ±1,5 °C distanță); până
atunci e 0. De ce 1 °C: într-o simulare (10 zile, afară 5 °C cu o variație
zilnică, predicții până la −10 °C), o casă cu o curbă de 0,05 °C/h pe °C a
greșit cu până la 540 de minute cât timp curba nu era învățată, iar o casă
fără curbă, cu o curbă mică greșită învățată, a greșit cu până la 90 de
minute. Cu 1 °C curba primei case s-a învățat (eroare de cel mult 8 minute)
când temperaturile ei de afară au avut o abatere de 1,5 °C; sub 1 °C o curbă
greșită a ajuns la 330 de minute. În câteva săptămâni de iarnă temperaturile
de afară variază mult mai mult de atât.

---

## 5. Cum se învață inerția

τ nu se poate calcula ca h și k (q depinde de el într-un mod curb). Integrarea
învață **zece candidați în același timp**, fiecare cu τ-ul lui:

```
0, 10, 20, 30, 45, 60, 90, 120, 180, 240 de minute
```

Pentru fiecare candidat q se urmărește cu τ-ul lui, iar h, c, k și s se potrivesc
ca în secțiunea 4. Înainte de a învăța dintr-un interval, fiecare candidat îl
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
grad), fără curbă, fără pierdere, fără inerție**, iar oprirea anticipată nu se calculează
(se folosește *Oprirea anticipată maximă* a camerei ca atare). Într-o cameră
locuită cele 4 + 4 ore se adună de obicei în prima zi.

---

## 7. Folosirea modelului

Toate predicțiile sunt o **simulare minut cu minut** cu modelul învățat,
pornind de la temperatura camerei și q de acum, pentru cel mult 24 de ore. După
ce s-a învățat un câștig solar, se socotește soarele fiecărui minut: înălțimea
soarelui la acea oră din zi și norii din prognoza orară pentru acea oră
(altfel norii de acum). O pornire sau o oprire anticipată socotește soarele
perioadei în care rulează (secțiunea 10).

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

### Relee: pornirea și oprirea după inerție

Pentru un releu, un termostat *Pornit / oprit (hvac mode)* sau TRV-uri cu
forțare (cererea lor de căldură după senzorul camerei) cu *Folosește inerția
învățată* pornit (implicit), în banda de histerezis:

- cu încălzirea pornită: simularea rulează **fără încălzire** de acum (q de
  acum, temperatura de afară de acum, soarele așteptat) până când camera începe
  să scadă; când cea mai mare temperatură a ei ajunge la **țintă + histerezis**,
  încălzirea se oprește acum;
- cu încălzirea oprită: simularea rulează **cu încălzire** până când camera
  începe să crească; când cea mai mică temperatură a ei ajunge la **țintă −
  histerezis**, încălzirea pornește acum.

La marginile benzii decide banda, ca înainte, iar timpii minimi pornit / oprit
se respectă în continuare. Exemplu (camera din secțiunea 2 cu τ = 60 de minute,
fără curbă, afară 5 °C, ținta 21 °C, histerezis 0,3, încălzindu-se de la
20,5 °C cu caloriferele reci): la 21,1 °C q e 0,84, iar simularea fără
încălzire ajunge la 21,37 °C, peste 21,3 °C, deci încălzirea se oprește la
21,1 °C; camera ajunge la 21,33 °C. Doar cu banda, încălzirea se oprește la
21,3 °C (q 0,87), iar camera ajunge la 21,55 °C. Simulări:
[ghid, capitolul 7](guide/07-anticipare-si-invatare.ro.md#pornirea-și-oprirea-după-inerție).

---

## 8. O casă fără temperatură de afară

Fără senzor de exterior și fără entitate meteo, pierderea nu poate depinde de
temperatura de afară: se învață ca **un număr constant de °C pe oră**
(`constant_loss: true`, `loss_per_hour` în °C pe oră). Este pierderea medie a
ultimelor săptămâni; zilele mai reci nu se văd. Nici curba de temperatură nu
se învață (are nevoie de temperatura de afară). Oprirea anticipată are nevoie
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

**Fără curbă de temperatură:**

| Cameră | model folosit după | h / c / k / τ învățate | eroare: medie / cea mai mare (minute) |
|---|---|---|---|
| Apartament izolat | 0,4 zile | 1,59 / −0,001 / 0,035 / 20 | 2 / 8 |
| Casă obișnuită | 0,5 zile | 2,78 / 0,000 / 0,070 / 30 | 2 / 5 |
| Casă veche | 0,8 zile | 3,75 / −0,008 / 0,100 / 20 | 9 / 18 |
| Încălzire în pardoseală | 0,7 zile | 1,60 / −0,001 / 0,040 / 180 | 2 / 7 |

Curba a ieșit aproape de 0, cum trebuie. La casa veche h și k au ieșit mai mici
în aceeași proporție (3,75 ÷ 0,100 ≈ 4,5 ÷ 0,12): camera vede rar diferențele
mari care le-ar deosebi, iar predicțiile rămân apropiate.

**Cu curbă de temperatură** (centrala dă cu 3 % mai multă căldură pentru
fiecare °C sub 5 °C afară: încălzire = putere × (1 + 0,03 × (5 − afară)) =
1,15 × putere − 0,03 × putere × afară, deci h adevărat este 1,15 × putere, iar
c adevărat 0,03 × putere):

| Cameră, cu curbă | h / c adevărate | h / c învățate | eroare cu curba învățată: medie / cea mai mare | eroare fără curbă (înainte): medie / cea mai mare |
|---|---|---|---|---|
| Apartament izolat | 1,84 / 0,048 | 1,82 / 0,047 | 4 / 6 | 28 / 56 |
| Casă obișnuită | 3,22 / 0,084 | 2,76 / 0,062 | 8 / 15 | 22 / 52 |
| Casă veche | 5,17 / 0,135 | 4,22 / 0,094 | 7 / 14 | 16 / 38 |
| Încălzire în pardoseală | 1,84 / 0,048 | 1,84 / 0,048 | 5 / 11 | 42 / 122 |

(Erori în minute. La casa obișnuită și la cea veche h, c și k au ieșit mai mici
împreună, din motivul de mai sus.)

---

## 10. Soarele

**Semnalul solar.** Cât soare poate ajunge acum în cameră, de la 0 la 1:

```
soare = max(0, sin(înălțimea soarelui)) × (1 − 0,75 × acoperire^3,4)
```

- **înălțimea soarelui** se calculează din oră și din locația din Home
  Assistant (formulele NOAA, cu o eroare de o fracțiune de grad). Nu se setează
  nimic pentru ea;
- **acoperirea** este acoperirea cu nori de la 0 (senin) la 1 (înnorat):
  `cloud_coverage` al entității meteo (și al fiecărei ore din prognoza ei),
  altfel presupusă din starea vremii: *sunny* / *clear-night* 0,1,
  *partlycloudy* și *windy* 0,5, *windy-variant* 0,7, *cloudy* 0,9, ploaie,
  zăpadă, grindină, ceață, furtună 1;
- `1 − 0,75 × acoperire^3,4` este partea din lumina soarelui care trece prin
  nori (Kasten și Czeplak, 1980): 1 pe cer senin, 0,93 la jumătate acoperit,
  0,48 la o acoperire de 0,9, 0,25 înnorat.

**Exemplu** (București, 44,4° N, 12 octombrie la prânz): soarele e la 36,7°,
sin 36,7° = 0,60. Cer senin: semnal 0,60; jumătate acoperit: 0,60 × 0,93 =
0,56; înnorat: 0,60 × 0,25 = 0,15. Noaptea semnalul e 0. Pe 15 noiembrie la
prânz soarele e la 27,2° (semnal 0,46 pe cer senin), pe 21 decembrie la 22,2°
(0,38).

s este câte °C pe oră adaugă un semnal de 1: o cameră cu s = 1,5 câștigă
1,5 × 0,30 = **0,45 °C/h** la un semnal de 0,30. Orientarea ferestrelor nu
trebuie dată: s este media pe orele de soare pe care le primește camera. O
cameră cu soare doar dimineața sau doar după-amiaza are un s mai mic; o cameră
fără soare, s = 0.

**Când se învață soarele.** Doar într-o casă cu entitate meteo (fără ea norii
nu se cunosc: s rămâne 0). Și doar când **se vede clar**:

- intervalele au avut destul soare: suma pătratelor semnalului solar mediu al
  intervalelor, uitată la fel ca intervalele, cel puțin **1** (de exemplu 12
  intervale la un semnal de 0,3: 12 × 0,3² = 1,08);
- s este la cel puțin **5 erori standard** de 0. Eroarea standard vine din
  eroarea pătratică obișnuită de predicție a intervalelor și din ecuațiile
  normale din secțiunea 4 (eroarea unui coeficient al metodei celor mai mici
  pătrate). Sub această limită, căldura intervalelor cu soare poate fi la fel
  de bine întâmplare, oameni sau gătit, iar s este 0.

De ce 5: într-o primă simulare fără această limită, o cameră spre nord în care
se gătește la prânz a învățat un soare de 0,24 – 0,40 °C/h la fiecare rulare,
iar predicțiile ei de zi s-au înrăutățit (eroare medie 0,07 – 0,09 °C înainte,
0,18 – 0,22 °C după). Cu 5, un soare de 2 °C/h se învață totuși în 9 zile (3
dintre ele senine) în testele integrării.

**Ce schimbă soarele.** **Pornirea anticipată** are nevoie de mai puțin într-o
dimineață însorită, **oprirea anticipată** poate începe mai devreme într-o
după-amiază însorită, iar **timpul până la țintă** și **temperatura prezisă**
din card urmează soarele. Exemplu (camera din secțiunea 2 cu s = 1,5, un
semnal constant de 0,3, afară 0 °C): de la 18 la 21 °C, pornind la rece,
**161 de minute** în loc de 231; de la 21 °C, tocmai încălzită (q = 1), până la
confortul de 20,5 °C, **149 de minute** în loc de 82.

**Setarea *Câștig solar* a camerei** este separată și rămâne: coboară ținta cât
e soare. Soarele învățat schimbă doar predicțiile, niciodată ținta.

**Simulări** (camere fictive, aceleași ipoteze ca în secțiunea 9, la 45° N la
jumătatea lui noiembrie; numerele sunt alese să fie plauzibile, nu sunt
măsurători):

- fiecare cameră: h = 2,5 °C/h, k = 0,06 pe oră, τ = 30 de minute;
- soarele printr-o fereastră: până la 2,2 °C/h pe cer senin cu soarele drept
  pe fereastră, proporțional cu cât de drept cade pe ea, plus 15 % din asta ca
  lumină difuză, slăbit de nori;
- fiecare zi senină (30 %), schimbătoare (40 %) sau înnorată (30 %); norii
  entității meteo diferă cu ±0,15 (abatere standard) de cei reali, cei din
  prognoză cu ±0,25;
- din ziua 15 până în ziua 40, la 09:00, 11:00, 13:00 și 15:00 (zi) și la 22:00
  (noapte), se prezice temperatura peste 3 ore fără încălzire și se compară cu
  cea reală; trei rulări cu vreme diferită.

Eroarea medie a predicției (°C), zi / noapte:

| Cameră | fără soare | cu soarele învățat | s învățat (°C/h) |
|---|---|---|---|
| Fereastră spre sud | 1,09 – 1,22 / 0,93 – 0,99 | 0,17 – 0,21 / 0,06 – 0,08 | 2,51 – 2,56 |
| Fereastră spre est | 0,36 – 0,38 / 0,22 – 0,23 | 0,26 – 0,30 / 0,04 | 0,74 – 0,80 |
| Fereastră spre vest | 0,49 – 0,55 / 0,34 – 0,37 | 0,36 – 0,41 / 0,19 – 0,23 | 0,92 – 0,98 |
| Nord, fără soare | 0,03 – 0,04 / 0,03 – 0,04 | la fel | 0 |
| Nord, gătit 12:00 – 13:30 (1 °C/h) | 0,45 – 0,46 / 0,10 – 0,13 | la fel | 0 în 2 rulări, 0,31 în 1 |

Fără termen solar modelul nu doar ratează soarele: pune căldura lui pe seama
încălzirii și a unei pierderi mai mici, deci și nopțile ies greșit. s iese
peste 2,2 la camera spre sud din cauza luminii difuze.

**O casă întreagă** (două zone ca camera de mai sus, un singur termostat,
senzorul în una dintre ele; zonele se egalizează cu 0,5 din diferența lor pe
oră cu ușile deschise, cu 0,15 cu ele mai mult închise):

| Casă | fără soare | cu soarele învățat | s învățat (°C/h) |
|---|---|---|---|
| Senzor în zona de sud, uși deschise | 0,70 – 0,76 / 0,44 – 0,49 | 0,21 – 0,23 / 0,03 – 0,04 | 1,44 – 1,48 |
| Senzor în zona de nord, uși deschise | 0,51 – 0,58 / 0,43 – 0,47 | 0,14 – 0,16 / 0,15 – 0,20 | 1,06 – 1,16 |
| Senzor în zona de nord, uși mai mult închise | 0,36 – 0,41 / 0,31 – 0,36 | 0,19 – 0,23 / 0,20 – 0,25 | 0,72 – 0,74 |
| Senzor într-o zonă spre est, cealaltă spre vest | 0,35 – 0,37 / 0,24 – 0,25 | 0,20 – 0,21 / 0,07 – 0,09 | 0,60 – 0,63 |

Un senzor fără soare propriu învață soarele care ajunge la el din cealaltă
zonă. S-a încercat și un model cu câte un termen solar pe fiecare latură a
casei (est, sud, vest): mai bun doar pentru ferestre spre est și vest, iar
într-o cameră spre nord a învățat un soare de est care nu exista în 2 din 3
rulări. De aceea există un singur termen.

---

## 11. Limite

- **Curba de temperatură este o linie dreaptă.** O centrală a cărei curbă se
  îndoaie sau care ajunge la temperatura maximă a apei la ger se învață ca
  linia dreaptă cea mai apropiată, pe ultimele săptămâni.
- **Un senzor cu pas mare (0,5 °C) pe vreme constantă.** Când o săptămână
  temperatura de afară se schimbă doar între zi și noapte, un astfel de senzor
  poate duce la o curbă de temperatură greșită. Într-o simulare (7 zile, afară
  0 – 10 °C între noapte și zi, fără curbă în casă, trei rulări) timpul de
  încălzire la −5 °C a ieșit greșit cu până la 48 %; cu un senzor de 0,1 °C cu
  cel mult 5 %, iar cu senzorul de 0,5 °C dar zile cu temperaturi diferite tot
  cu cel mult 5 %. Se corectează singur când apar zile cu alte temperaturi;
  *Pornirea anticipată maximă* a camerei limitează în continuare pornirea.
- **Diferențele de la o zi la alta nu se învață.** Oamenii, gătitul sau pereții
  mai reci după o absență lungă schimbă camera; metoda celor mai mici pătrate
  le face media. Soarele se învață ca medie pe orele în care ajunge în cameră:
  jaluzelele trase, zăpada de afară sau un copac cu sau fără frunze îl schimbă
  până când ultimele săptămâni îl urmează.
- **Norii sunt cei ai entității meteo.** O prognoză greșită a norilor înseamnă
  un soare greșit în predicție; învățarea folosește norii de acum.
- **Robinete termostatice cu o centrală pornită de un termostat care nu este în
  Home Assistant**: integrarea nu poate ști când merge centrala; învățarea nu
  este de încredere, iar pornirea / oprirea anticipată nu sunt recomandate.
- **Așteptările dinainte de pornirea sursei de căldură** (timpii minimi de
  pornire / oprire, *Camere necesare pentru pornirea sursei*, camera de
  referință) nu sunt încălzire: pornirea poate întârzia cu acea așteptare.
- **Învățarea salvată înainte de 2.6** (episoade de încălzire și răcire) nu se
  potrivește noului model și se renunță la ea: după actualizare fiecare cameră
  învață din nou, în circa o zi. Învățarea din versiunile beta 2.6.0 se
  păstrează; soarele ei pornește de la 0.

---

## 12. Unde se vede

**`sensor.<cameră>_heating_rate`** – stare: minute pe grad cu încălzirea
complet pornită, la temperatura camerei și cea de afară de acum (`min/°C` sau
`min/°F`). Atribute:

| Atribut | Semnificație |
|---|---|
| `learned` | se folosește modelul învățat (secțiunea 6) |
| `heating_per_hour` | h (la 0 °C afară) |
| `weather_curve` | c (°C pe oră în plus pentru fiecare °C mai frig afară) |
| `sun_gain` | s (°C pe oră la un semnal solar de 1; 0 cât timp nu se vede clar) |
| `loss_per_hour` | k (pe oră sau, cu `constant_loss`, °C pe oră) |
| `constant_loss` | pierderea este constantă (secțiunea 8) |
| `inertia_minutes` | τ |
| `heat_reaching_now` | q acum |
| `error_per_hour` | eroarea obișnuită de predicție a unui interval (°C pe oră) |
| `minutes_per_degree` | minute pe grad la −10 / 0 / 10 / 20 °C (14 / 32 / 50 / 68 °F) afară |
| `hours_heating`, `hours_idle`, `hours_needed` | progresul învățării (secțiunea 6) |
| `model` | modelul în °C (h, c, k, s, τ, q, pierdere constantă, temperatura medie de afară, `band` și `inertia_control`: cum pornește și oprește dispozitivul încălzirea) pentru predicția cardului; gol până se învață |

**`sensor.<casă>_outdoor_average`** – atributul `sun_forecast`: semnalul solar
așteptat la fiecare 15 minute pentru următoarele 12 ore (cu entitate meteo).

**`sensor.<cameră>_cooling_rate`** – stare: cât de repede scade acum camera
fără încălzire (°C/h, gol până se învață); atribute: `learned`,
`loss_per_hour`, `inertia_minutes`, toleranța opririi anticipate.

**`sensor.<cameră>_decision`** – `next_estimate` (când începe următoarea
pornire / oprire anticipată, cu ce temperatură de afară și dacă este învățată
sau implicită) și `time_to_target`.

**`button.<cameră>_reset_learning`** – uită modelul camerei (și în *Detalii* pe
card, cu un al doilea clic pentru confirmare).

**Card, Detalii** – grupul *Învățare*: *Învățare* (*învățat · eroare obișnuită
±0,12 °C/h* sau, în timpul învățării, *se învață… 2 din 4 h cu încălzire, 1 din
4 h fără*, cu valoarea implicită dedesubt) cu butonul **Resetează**; după ce
s-a învățat, *Încălzire învățată* (minute pe grad acum și inerția, de ex.
*45 min/°C acum · inerție 30 min*), *Curba de temperatură* (*+0.050 °C/h
pentru fiecare °C mai frig afară* sau *fără*), *Soare* după ce s-a învățat
(*+1.50 °C/h cu soarele la zenit pe cer senin · acum +0.60 °C/h*: s și s ×
semnalul solar de acum) și *Pierdere de căldură învățată* (*scade 0,70 °C/h
acum*).

**Card, grafic** – după ce s-a învățat, temperatura prezisă pentru următoarele
12 ore (punctat): modelul din secțiunea 2 simulat minut cu minut după ținta
planificată, cu prognoza orară și soarele așteptat. Încălzirea pornește și se
oprește cum o face dispozitivul (`band` din atributul `model`, °C sub și peste
țintă): *cold* / *hot tolerance* ale Generic Thermostat (câte 0,3 °C când nu
le spune), histerezisul pentru relee, control pornit / oprit, forțarea TRV și
termostatele fără `hvac_action`, cu pornirea și oprirea după inerție din
secțiunea 7 când `inertia_control` e pornit. Termostatele și TRV-urile care se
reglează singure nu au bandă: predicția ține ținta și desenează încălzirea lor
ca o singură perioadă.

**Diagnostic** – `thermal_model` cu toate numerele modelului și cei zece
candidați de inerție (fiecare cu h, c, k, s, eroarea, `outdoor_spread`,
abaterea temperaturilor de afară ale încălzirii lui, secțiunea 4, și
`sun_seen`, suma pătratelor semnalului solar, secțiunea 10).
