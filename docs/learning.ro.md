# Cum învață Smart Heating Control (încălzire și răcire)

*[English](learning.md)*

Documentul explică în detaliu cum învață fiecare cameră cât durează să se
încălzească și cât de repede se răcește, cum se calculează numerele și cum
sunt folosite pentru **pornirea anticipată**, **oprirea anticipată** și
**timpul până la țintă** afișat pe card. Fiecare număr din exemple este fie
calculat în text, fie precizat ca ipoteză a exemplului.

Intern toate calculele se fac în °C; la o casă în °F se convertește doar
afișarea (1 °C = 1,8 °F).

- [1. De ce învățare](#1-de-ce-învățare)
- [2. Episoadele de încălzire](#2-episoadele-de-încălzire)
- [3. Modelul încălzirii](#3-modelul-încălzirii)
- [4. Cum se calculează cele trei numere](#4-cum-se-calculează-cele-trei-numere)
- [5. Când se folosește un termen și valorile imposibile](#5-când-se-folosește-un-termen-și-valorile-imposibile)
- [6. Ce episoade se păstrează](#6-ce-episoade-se-păstrează)
- [7. Folosirea modelului încălzirii](#7-folosirea-modelului-încălzirii)
- [8. Învățarea răcirii și oprirea anticipată](#8-învățarea-răcirii-și-oprirea-anticipată)
- [9. Simulări fictive](#9-simulări-fictive)
- [10. Limite](#10-limite)
- [11. Unde se vede](#11-unde-se-vede)

---

## 1. De ce învățare

Ca să fie 21 °C în cameră la 07:00, încălzirea trebuie să pornească mai
devreme. Cât de devreme depinde de cameră: sursa de căldură, caloriferele sau
încălzirea în pardoseală, izolația, temperatura de afară. În loc să ceară
aceste valori, fiecare cameră își măsoară propriul comportament și învață din
el.

---

## 2. Episoadele de încălzire

Un **episod** este o încălzire măsurată: din momentul în care camera începe să
ceară căldură până ajunge la țintă sau se oprește încălzirea.

**Începutul.** Un episod începe când camera cere căldură și temperatura ei e
cu cel puțin **toleranța** sub țintă. Toleranța nu este o setare nouă; se ia
de unde o are deja camera:

| Controlul camerei | Toleranța folosită |
|---|---|
| Generic Thermostat | `cold_tolerance` al lui |
| Releu, control pornit / oprit | *Histerezisul* camerei |
| Alte termostate | *Thermostat tolerance* al camerei (implicit 0) |

Exemplu: ținta 22 °C, toleranța 0,5 °C → un episod poate începe de la 21,5 °C
sau mai jos (22 − 0,5 = 21,5).

**Sfârșitul.** Episodul se termină când camera ajunge la țintă sau se oprește
cererea de căldură. Se **folosește** doar dacă:

- cererea de căldură a durat **cel puțin 10 minute**;
- temperatura a **crescut**, oricât de puțin (o creștere lentă e reală și se
  învață);
- niciun **senzor de fereastră sau ușă** al camerei (sau unul legat) nu a fost
  deschis;
- **sursa de căldură a mers** tot timpul cât s-a considerat încălzire
  (`hvac_action` al Generic Thermostat, releul sau termostatul pornit / oprit
  pornit, *Sursa de căldură* a casei dacă e setată);
- este **sezonul rece** (nu modurile Oprit sau Vară, nu în afara sezonului de
  încălzire).

**Ce se salvează** pentru fiecare episod:

| Câmp | Exemplu | Înțeles |
|---|---|---|
| afară | 5,0 | temperatura medie de afară în timpul episodului (°C), sau gol dacă nu se știe |
| grade | 2,0 | cu câte °C a urcat camera |
| minute | 125 | cât a durat |
| la | 2026-10-20T07:00 | când s-a terminat |

Minutele se numără din momentul în care camera **chiar încălzește** (cere
căldură și sursa ei de căldură funcționează) până la sfârșit. Sunt incluse:
încălzirea centralei, a apei și a caloriferelor. **Nu** sunt incluse:
timpul de dinaintea pornirii sursei — timpii minimi pornit / oprit ai unui
releu sau ai sursei de căldură a casei și așteptarea altor camere (*Camere
necesare pentru pornirea sursei* sau camera de referință). Niciunul nu trebuie cunoscut sau
configurat, dar pornirea anticipată poate începe cu acea așteptare mai
târziu, pentru că ea nu se învață.

---

## 3. Modelul încălzirii

Timpul de încălzire se învață ca:

```
minute = parte fixă + grade × minute pe grad
minute pe grad = M + S × afară
```

| Număr | Numele în atribute | Înțeles |
|---|---|---|
| partea fixă (F) | `fixed_minutes` | minutele până începe camera să urce (pornirea sursei, încălzirea caloriferelor); aceleași la o urcare mică și la una mare |
| M | `minutes_per_degree_at_0` (diagnostice) | minute pe °C când afară sunt 0 °C |
| S | `per_outdoor_degree` | cum se schimbă minutele pe °C la fiecare °C afară (de obicei negativ: mai cald afară, mai repede) |

**Exemplu** (valori presupuse pentru exemplu): F = 25 de minute, M = 60,
S = −2. La 5 °C afară, minutele pe grad sunt 60 + (−2 × 5) = 50. Pentru o
urcare de 3 °C: 25 + 3 × 50 = **175 de minute**.

### De ce o parte fixă

Versiunile dinainte de 2.0 învățau o singură viteză pe episod (grade ÷ ore).
Asta amestecă partea fixă în viteză. Cu camera din exemplul de mai sus
(F = 25, 50 de minute pe grad la 5 °C):

- o recuperare mică de 0,4 °C durează 25 + 0,4 × 50 = 45 de minute → viteza
  0,4 ÷ 0,75 h = **0,53 °C/h**;
- o urcare de 3 °C după un setback de noapte durează 25 + 3 × 50 = 175 de
  minute → viteza 3 ÷ 2,92 h = **1,03 °C/h**.

Dacă 60 % dintre episoade sunt mici și 40 % mari, viteza medie este
0,6 × 0,53 + 0,4 × 1,03 = **0,73 °C/h**. Pentru o urcare de 3 °C rezultă
3 ÷ 0,73 = 4,1 h = **247 de minute**, față de 175 reale: **cu 72 de minute
prea devreme**, iar mai multe episoade nu repară asta, pentru că media rămâne
aceeași. Partea fixă elimină această eroare.

### De ce temperatura de afară e o linie dreaptă

Când e mai frig afară camera pierde mai multă căldură, deci fiecare grad
durează mai mult. O centrală cu curbă de termoreglare face invers: mai frig
afară, apă mai fierbinte, încălzire mai rapidă. Un singur număr, S, cuprinde
ambele efecte împreună, așa cum sunt ele în casa respectivă, fără să trebuiască
separate.

---

## 4. Cum se calculează cele trei numere

F, M și S sunt valorile pentru care duratele calculate ale tuturor episoadelor
păstrate sunt **cât mai aproape** de cele măsurate: suma pătratelor
diferențelor este cea mai mică posibilă (**metoda celor mai mici pătrate**). Nu
e încercare la întâmplare: condiția dă trei ecuații cu trei necunoscute, iar
soluția lor este acel minim.

### Exemplu calculat

Patru episoade ale unei camere fictive (făcute cu F = 25, M = 60, S = −2, ca
rezultatul să poată fi verificat):

| Episod | grade (g) | afară (o) | minute (d) | cum a fost făcut |
|---|---|---|---|---|
| A | 0,4 | 10 | 41 | 25 + 0,4 × (60 − 2 × 10) = 25 + 0,4 × 40 |
| B | 3,0 | 0 | 205 | 25 + 3 × 60 |
| C | 2,0 | 5 | 125 | 25 + 2 × (60 − 2 × 5) = 25 + 2 × 50 |
| D | 0,5 | 0 | 55 | 25 + 0,5 × 60 |

Integrarea vede doar g, o și d.

**Pasul 1: sumele.**

| Sumă | Calcul | Valoare |
|---|---|---|
| numărul de episoade | | 4 |
| Σ g | 0,4 + 3 + 2 + 0,5 | 5,9 |
| Σ g·o | 0,4·10 + 3·0 + 2·5 + 0,5·0 = 4 + 0 + 10 + 0 | 14 |
| Σ g² | 0,16 + 9 + 4 + 0,25 | 13,41 |
| Σ g²·o | 0,16·10 + 9·0 + 4·5 + 0,25·0 = 1,6 + 20 | 21,6 |
| Σ (g·o)² | 4² + 0 + 10² + 0 = 16 + 100 | 116 |
| Σ d | 41 + 205 + 125 + 55 | 426 |
| Σ g·d | 16,4 + 615 + 250 + 27,5 | 908,9 |
| Σ g·o·d | 4·41 + 0 + 10·125 + 0 = 164 + 1250 | 1414 |

**Pasul 2: cele trei ecuații** (fiecare sumă la locul ei):

```
   4 × F +  5,9  × M +  14  × S =  426
 5,9 × F + 13,41 × M + 21,6 × S =  908,9
  14 × F + 21,6  × M + 116  × S = 1414
```

**Pasul 3: soluția** (eliminare Gauss, în cod): **F = 25, M = 60, S = −2**.
Verificare în prima ecuație: 4 × 25 + 5,9 × 60 + 14 × (−2) = 100 + 354 − 28 =
426. ✓

**Pasul 4: folosirea.** Mâine camera are 18 °C și trebuie să ajungă la 21 °C,
cu o prognoză medie de −3 °C (nevăzută în episoade): minute pe grad
60 + (−2 × −3) = 66, minute 25 + 3 × 66 = **223**. Linia se prelungește dincolo
de ce s-a văzut; *Anticiparea maximă* a camerei o limitează în continuare.

**Temperatura de afară necunoscută** (fără senzor, fără prognoză): se
folosește media temperaturilor de afară ale episoadelor, aici
(10 + 0 + 5 + 0) ÷ 4 = 3,75 °C → 60 + (−2 × 3,75) = 52,5 minute pe grad.

Cu episoade reale duratele nu sunt exacte (soare, oameni, gătit, treapta
senzorului), deci nu există trei numere care să se potrivească tuturor;
metoda celor mai mici pătrate le alege pe cele care se potrivesc cel mai bine.
Calculul se reface după fiecare episod și durează sub o milisecundă pentru 50
de episoade.

---

## 5. Când se folosește un termen și valorile imposibile

Un termen se calculează doar când episoadele îl pot deosebi de ceilalți.

**Partea fixă cere episoade de mărimi diferite**: cel mai mare minus cel mai
mic trebuie să fie de cel puțin **1 °C**. De ce: două episoade de 0,4 °C care au
durat câte 45 de minute pot fi explicate de 25 + 0,4 × 50, de 5 + 0,4 × 100
sau de 45 + 0,4 × 0 (toate dau 45). Doar un episod de altă mărime, de exemplu
3 °C în 175 de minute, lasă un singur răspuns: 25 + 3 × 50 = 175, pe când
5 + 3 × 100 = 305 și 45 + 3 × 0 = 45 nu se potrivesc. Valoarea de 1 °C a fost
aleasă pentru că, la treapta obișnuită a senzorului de 0,1 °C, eroarea de
citire este atunci cel mult 10 % din diferență (0,1 ÷ 1).

**Termenul de afară cere temperaturi de afară care diferă cu cel puțin
1 °C** (între episoadele care au temperatura de afară). Sub atât, înclinarea
liniei ar fi ghicită din zgomot.

Până se poate folosi, un termen este zero; formula rămâne aceeași:

| Episoade | Ce se calculează |
|---|---|
| niciunul | implicit: 60 de minute pe grad, fără parte fixă (1 °C pe oră) |
| aceeași mărime, aceeași temperatură afară | doar minutele pe grad |
| aceeași mărime, temperaturi de afară diferite | minutele pe grad și termenul de afară |
| mărimi diferite, aceeași temperatură afară | partea fixă și minutele pe grad |
| mărimi și temperaturi de afară diferite | toate trei |

**Valorile imposibile se pun pe zero și restul se recalculează:**

- **parte fixă negativă** (posibilă din zgomot) → partea fixă 0, recalculat
  fără ea;
- minute pe grad **negative la cea mai rece sau cea mai caldă temperatură de
  afară învățată** → se renunță la termenul de afară, recalculat;
- **episoadele mari nu sunt mai lente decât cele mici** (minute pe grad
  negative fără termen de afară) → rămâne doar o parte fixă, media
  episoadelor. Exemplu: 0,5 °C în 300 de minute și 2,5 °C în 100 de minute →
  partea fixă (300 + 100) ÷ 2 = 200 de minute;
- departe de temperaturile de afară învățate linia poate trece prin zero:
  acolo minutele pe grad nu scad niciodată **sub zero**.

**Încălzește deja.** Când camera e deja într-un episod, timpul cât a încălzit
se scade din partea fixă, pentru că apa și caloriferele sunt deja calde.
Exemplu: parte fixă 30 de minute, 40 de minute pe grad, 1 °C de urcat: înainte
de încălzire 30 + 40 = 70 de minute; după 20 de minute de încălzire
(30 − 20 =) 10 + 40 = 50 de minute; după o oră 0 + 40 = 40 de minute.

---

## 6. Ce episoade se păstrează

Se păstrează ultimele **25 de episoade mici** (sub 1 °C) și ultimele **25 de
episoade mari** (1 °C sau mai mult), în ordinea timpului. Un episod nou scoate
din memorie cel mai vechi episod **de același fel**.

De ce separat: un termostat care menține temperatura face multe cicluri mici
(de exemplu 6 pe zi), iar o urcare mare apare o dată pe zi sau o dată pe
săptămână. Cu o singură listă a ultimelor 30, ciclurile mici le scot pe cele
mari: în simularea de la secțiunea 9.3 rămâneau doar 4 episoade mari din 30,
iar partea fixă nu putea fi învățată bine. Cu 25 + 25 episoadele mari rămân.

La aproximativ un episod mare pe zi, cele 25 de episoade mari se înnoiesc în
aproximativ 25 de zile, deci după o schimbare (altă curbă de termoreglare,
calorifere noi) învățarea o urmează în câteva săptămâni. Ca să înceapă imediat
de la zero, fiecare cameră are butoanele **Reset heating learning** și **Reset
cooling learning** (și în *Detaliile* cardului, lângă fiecare învățare, cu un
al doilea clic pentru confirmare).

### Episoade departe de celelalte

O ușă lăsată deschisă în timpul unei încălziri, gătitul, un senzor care a sărit:
un astfel de episod durează mult mai mult (sau mai puțin) decât celelalte și ar
trage calculul spre el. Cu cel puțin 8 episoade, fiecare episod e comparat cu
ce spune calculul din toate (minutele lui minus minutele calculate). Diferența
obișnuită este mediana abaterilor absolute față de mediană, scalată la o
abatere standard (× 1,4826). Un episod aflat la peste **3,5 ori** diferența
obișnuită (cel puțin 1 minut) e lăsat deoparte și restul se recalculează, o
singură dată. Trebuie să rămână cel puțin 5 episoade, altfel se folosesc toate.

Nimic nu e potrivit pe o anumită casă: „departe” se măsoară din episoadele
camerei. Episodul lăsat deoparte rămâne păstrat: când camera chiar s-a schimbat
(calorifere noi), episoadele noi devin repede mai multe decât cele vechi și
calculul le urmează. Senzorul *Viteză de încălzire* arată câte sunt lăsate
deoparte (`episodes_left_out`).

**Exemplu.** Zece episoade de 20 de minute + 30 de minute pe grad (2 °C în 80
de minute) și unul de 2 °C în 300 de minute (o fereastră deschisă fără senzor).
Calculate împreună, 2 °C ies în aproximativ 104 minute; fără episodul
depărtat, în 80.

**Verificat în simulări** de case (câte două luni de iarnă, senzori cu zgomot
și goluri, gătit, ferestre deschise fără senzori): cam aceeași eroare ca înainte
în casele stabile și clar mai aproape după o schimbare a casei (calorifere cu
50 % mai puternice): în cele 3 săptămâni de după schimbare, eroarea medie a
timpului de încălzire a scăzut de la 33 la 28 de minute, iar mai târziu 90 % din
estimări au fost în 28 de minute, în loc de 37.

---

## 7. Folosirea modelului încălzirii

### Pornirea anticipată

Pentru următoarea schimbare din program spre un nivel mai cald (de exemplu
*Sleep* 19 °C → *Home* 22 °C la 07:00):

1. grade = nivelul presetului următor − temperatura camerei acum. Exemplu:
   22 − 19,5 = **2,5 °C**.
2. afară = **media prognozei** între pornire și 07:00 (cu o entitate meteo cu
   prognoză orară; altfel valoarea măsurată). Pornirea depinde de această
   temperatură, iar temperatura depinde de pornire, așa că se calculează de **3 ori**,
   de fiecare dată din perioada găsită înainte.
3. minute = modelul încălzirii (secțiunea 3). Exemplu cu F = 25, M = 60,
   S = −2 și o prognoză medie de 5 °C: 25 + 2,5 × 50 = **150 de minute**.
4. pornirea nu e **niciodată mai devreme** decât *Anticiparea maximă* a
   camerei. Cu un maxim de 120 de minute pornirea e la 07:00 − 120 de minute =
   05:00, altfel la 07:00 − 150 de minute = 04:30.
5. odată pornită continuă până la 07:00, chiar dacă se face cald mai devreme.

### Timpul până la țintă

Cât timp o cameră e sub țintă, cardul arată timpul până la țintă (*~35 min*),
cu același model, temperatura de afară de acum și timpul deja încălzit
(secțiunea 5).

### Înainte de primul episod

Se folosește valoarea implicită: **60 de minute pe grad, fără parte fixă**.
Cardul arată *se învață…* cu un rând mic dedesubt: *implicit 60 min/1°C*
(33 min/1°F la o casă în °F, pentru că 60 ÷ 1,8 = 33,3).

---

## 8. Învățarea răcirii și oprirea anticipată

### Episoadele de răcire

Un episod de răcire durează de la sfârșitul unei cereri de căldură până la
începutul următoarei și se folosește dacă a durat cel puțin 10 minute,
temperatura a scăzut, oricât de puțin, și niciun senzor de fereastră sau ușă
nu a fost deschis.

### Coeficientul

O cameră pierde căldură proporțional cu cât este mai caldă decât afară:

```
T(t) = afară + (început − afară) × e^(−k × ore)
k = ln[(început − afară) ÷ (sfârșit − afară)] ÷ ore
```

**Exemplu** (fictiv): afară 0 °C, camera scade de la 21 °C la 19,6 °C în 2 ore.

- (21 − 0) ÷ (19,6 − 0) = 1,0714
- ln(1,0714) = 0,0690
- k = 0,0690 ÷ 2 = **0,0345 pe oră**

Camera pierde 0,0345 °C pe oră pentru fiecare grad cu care e mai caldă decât
afară: la 21 °C și 0 °C afară, 21 × 0,0345 = 0,72 °C pe oră; la 21 °C și
10 °C afară, 11 × 0,0345 = 0,38 °C pe oră. Se păstrează un singur coeficient
pe cameră: **media ultimelor 30** de episoade de răcire.

### Oprirea anticipată

Înaintea unei schimbări spre un nivel mai rece, încălzirea se oprește mai
devreme, cât timp camera rămâne în **confortul** nivelului curent: nivel −
toleranță. Exemplu: *Home* 21 °C, toleranța 0,5 °C → confort până la 20,5 °C.

```
minute = ln[(cameră − afară) ÷ (confort − afară)] ÷ k × 60
```

Cu k = 0,0345, camera 21 °C, confortul 20,5 °C:

- la 0 °C afară: ln(21 ÷ 20,5) = 0,0241 → 0,0241 ÷ 0,0345 × 60 = **42 de
  minute**;
- la 10 °C afară: ln(11 ÷ 10,5) = 0,0465 → 0,0465 ÷ 0,0345 × 60 = **81 de
  minute**.

Oprirea nu e niciodată mai lungă decât maximul *Optimal stop* al camerei;
până se învață răcirea se folosește maximul. Dacă în timpul opririi camera
scade sub confort, oprirea se anulează și revine nivelul curent până la
schimbare. Cu prognoză orară se folosește media prognozei din perioada
opririi, în 3 treceri, ca la pornire.

---

## 9. Simulări fictive

Simulările de mai jos compară învățarea versiunii 2.0 cu cea din 1.x. Folosesc
**case fictive**: numerele sunt alese să fie plauzibile, nu sunt măsurători.

### 9.1 Casele fictive

Fiecare casă se încălzește astfel: urcare pe oră = putere − k × (înăuntru −
afară), după o întârziere fixă.

| Casă | Întârziere | Putere (°C/h) | k (pe oră) |
|---|---|---|---|
| Apartament izolat | 15 min | 1,6 | 0,035 |
| Casă medie | 24 min | 2,8 | 0,07 |
| Casă veche, slab izolată | 30 min | 4,5 | 0,12 |
| Încălzire în pardoseală (lentă) | 90 min | 1,6 | 0,04 |

**Cu curbă de termoreglare**: temperatura pe tur este 35 + 0,8 × (14,5 − afară)
(cu 0,8 °C mai mult pe tur la fiecare °C mai frig, de exemplu 41 °C la 7 °C și
35 °C la 14,5 °C), iar puterea este proporțională cu (tur − cameră), scalată
să fie puterea din tabel la 5 °C afară.

### 9.2 Versiunea 2.0 față de 1.x

Ipoteze:

- 80 de zile, temperatura de afară aleatoare între −5 și 10 °C în fiecare zi;
- trei programe: **setback în fiecare noapte** (8 ore fără încălzire de la
  21 °C, nu sub 17 °C), **setback doar în weekend**, **fără setback**
  (dimineața pornește de la 0,3 – 0,6 °C sub 21 °C);
- 6 cicluri de termostat pe zi, de 0,1 – 0,3 °C;
- citirea senzorului rotunjită la treapta lui (0,1 °C sau 0,5 °C); toleranța
  0,3 sau 0 °C; cu și fără curbă de termoreglare;
- ±7 % zgomot aleator pe fiecare durată;
- primele 50 de zile învață, se prezic diminețile din zilele 51 – 80 (învățarea
  continuă și în ele).

4 case × 2 curbe × 2 toleranțe × 2 trepte ale senzorului = **32 de combinații**
pe program, câte 3 repetări.

| Program | 1.x: eroare medie | 2.0: eroare medie | Combinații în care 2.0 e mai proastă |
|---|---|---|---|
| Setback în fiecare noapte | 173 min | 4 min | 0 din 32 |
| Setback în weekend | 92 min | 4 min | 0 din 32 |
| Fără setback | 16 min | 11 min | 0 din 32 |

(Eroarea medie: media diferențelor absolute dintre durata prezisă și cea
reală, apoi media pe cele 32 de combinații.)

Câștigul mare vine din urcările mari după setback (secțiunea 3, *De ce o parte
fixă*). Fără setback urcările sunt mici și cele două versiuni sunt apropiate.

### 9.3 Episoade mici și mari păstrate separat

Aceleași case, setback în fiecare noapte, treapta senzorului 0,1 °C,
**toleranța 0** (cazul în care ciclurile termostatului intră în învățare), 300
de dimineți pe casă. Valori: eroarea medie / cea mai mare, în minute, și câte
episoade mari erau în memorie, în medie.

| Casă (fără curbă) | ultimele 30 | 15 mici + 15 mari | 25 mici + 25 mari |
|---|---|---|---|
| Apartament izolat | 9 / 64 (4 mari) | 6 / 34 (15) | 6 / 25 (25) |
| Casă medie | 8 / 53 | 6 / 29 | 5 / 23 |
| Casă veche | 6 / 43 | 5 / 24 | 4 / 19 |
| Pardoseală | 15 / 97 | 10 / 55 | 9 / 42 |

Cu toleranța 0,3 °C cele trei dau rezultate apropiate (de exemplu apartamentul
izolat 6 / 23, 6 / 22 și 5 / 23), deci păstrarea separată nu costă nimic când
nu e necesară.

### 9.4 Cât de diferite trebuie să fie temperaturile de afară

Cazul cel mai greu: 50 de zile de învățare cu o temperatură de afară care se
schimbă **foarte puțin** (între 5 °C și 5 °C + schimbarea din tabel), apoi 30
de zile între −5 și 10 °C, mult în afara celor învățate. Apartament izolat cu
curbă de termoreglare, eroarea medie / cea mai mare, în minute:

| Afară s-a schimbat în învățare | prag 0,5 °C | 1 °C | 2 °C | 3 °C |
|---|---|---|---|---|
| 1 °C | 5 / 143 | 4 / 34 | 4 / 34 | 4 / 34 |
| 2 °C | 4 / 87 | 4 / 87 | 4 / 36 | 4 / 36 |
| 3 °C | 4 / 74 | 4 / 74 | 4 / 74 | 4 / 39 |

Eroarea medie nu depinde de prag; doar cazul cel mai rău, și doar în **primele
3 zile** de vreme nouă. Cu pragul de 1 °C, cazul „2 °C” de mai sus:

| Zilele vremii noi | 1 – 3 | 4 – 7 | 8 – 14 | 15 – 30 |
|---|---|---|---|---|
| eroare medie / cea mai mare (min) | 12 / 87 | 5 / 20 | 4 / 11 | 3 / 14 |

Episoadele noi se învață și eroarea scade singură. 0,5 °C rămâne mai slab și
mai târziu, de aceea s-a ales 1 °C.

### 9.5 Curba de termoreglare: de ce un singur termen de afară

O primă idee a fost un model fizic (putere de încălzire fixă plus răcirea
învățată). Fără curbă de termoreglare e puțin mai bun decât 2.0; **cu** curbă e
clar mai slab, pentru că puterea se schimbă cu vremea:

| Casă, cu curbă | 1.x | model fizic | 2.0 |
|---|---|---|---|
| Apartament izolat | 41 | 31 | 3 |
| Casă medie | 38 | 19 | 2 |
| Casă veche | 54 | 13 | 1 |
| Pardoseală | 177 | 39 | 8 |

(Eroarea medie în minute pe cinci situații de test: 18 → 21 °C la 5, −5 și
12 °C afară, 19 → 21 °C la 0 °C, 20,5 → 21 °C la 5 °C; 30 de episoade învățate,
60 % mici.)

---

## 10. Limite

- **Diferențele de la o zi la alta nu se învață.** Aceeași urcare poate dura
  diferit din cauza soarelui, oamenilor, gătitului sau pentru că pereții sunt
  mai reci după o absență lungă. Metoda celor mai mici pătrate le mediază; nu
  le poate prezice. În practică eroarea scade până la mărimea acestor
  diferențe și nu mai jos.
- **Schimbările sursei de căldură** (altă curbă de termoreglare, alt setpoint
  pe zona centralei) se învață din nou în episoadele următoare (secțiunea 6).
- **TRV-uri cu o centrală pornită de un termostat care nu e în Home
  Assistant**: integrarea nu poate ști când merge efectiv centrala; învățarea
  nu e sigură, iar pornirea / oprirea anticipată nu sunt recomandate.
- **Învățarea salvată înainte de 2.0** păstra doar o viteză pe episod, fără
  grade și minute, deci nu se poate converti: încălzirea se învață din nou după
  actualizare. Răcirea se păstrează.

---

## 11. Unde se vede

**`sensor.<room>_heating_rate`** – starea: minutele pe grad la temperatura de
afară de acum (`min/°C` sau `min/°F`). Atribute:

| Atribut | Înțeles |
|---|---|
| `fixed_minutes` | partea fixă |
| `minutes_per_degree` | minute pe grad la −10 / 0 / 10 / 20 °C (14 / 32 / 50 / 68 °F) |
| `per_outdoor_degree` | schimbarea minutelor pe grad la fiecare grad afară |
| `uses_fixed`, `uses_outdoor` | ce termeni se folosesc (secțiunea 5) |
| `episodes`, `large_episodes` | episoadele păstrate și câte dintre ele sunt mari |
| `learning_starts_below_target` | toleranța de la care începe un episod |
| `last_episodes` | ultimele 5 episoade (afară, urcare, minute, ora) |

**`sensor.<room>_cooling_rate`** – starea: cât de repede scade camera acum fără
încălzire (°C/h); atribute: coeficientul, episoadele, toleranța.

**`sensor.<room>_decision`** – `next_estimate` (când începe următoarea pornire /
oprire anticipată, cu ce temperatură de afară și dacă e învățată sau
implicită) și `time_to_target`.

**Card, Detalii** – grupul *Învățare*: *Învățare încălzire* (numărul de
episoade, partea fixă și minutele pe grad acum, de exemplu *12 episoade ·
25 min + 49 min/°C acum*) și *Învățare răcire*, fiecare cu butonul
**Resetează**, apoi ultimul episod de încălzire (*+0.2° în 167 min, afară
12.0°, 09:11*); grupul *Program*: următoarea pornire / oprire anticipată.

**Diagnostice** – `learned_heating`, cu toate numerele modelului.
