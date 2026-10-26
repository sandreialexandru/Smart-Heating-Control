# 7. Pornirea și oprirea anticipată, învățarea

*[English](07-optimal-start-stop-and-learning.md) · [Cuprins](README.ro.md)*

Capitolul explică pe înțelesul tuturor cum învață fiecare cameră și cum
folosește ce a învățat. Calculele complete, cu toate cazurile și simulările,
sunt în [Cum învață integrarea](../learning.ro.md).

## De ce e nevoie de anticipare

Programul spune „`home` 21 °C de la 07:00”. Fără anticipare, încălzirea
pornește la 07:00 și camera e caldă abia pe la 08:30. Cu **pornirea
anticipată**, integrarea pornește încălzirea mai devreme, ca la 07:00 camera să
fie deja la 21 °C.

Invers, programul spune „`sleep` 18 °C de la 22:00”. Camera e caldă și s-ar
răci oricum încet. Cu **oprirea anticipată**, nivelul mai rece începe puțin mai
devreme, cât timp camera rămâne confortabilă până la 22:00. Se economisește
energie fără să simți diferența.

Ambele se pornesc pe cameră, la pasul *Program* (vezi
[capitolul 3](03-camere.ro.md#pasul-7-program)). Oprirea anticipată are nevoie
de o temperatură de afară (senzor sau entitate meteo).

## Cum învață o cameră să se încălzească

Nu trebuie să spui nimic despre casă (calorifere, izolație, centrală). Camera
își **măsoară singură** încălzirile, numite **episoade**:

- un episod începe când camera cere căldură, e cu cel puțin *toleranța* sub
  țintă și sursa ei de căldură chiar merge;
- se termină când camera ajunge la țintă sau încălzirea se oprește;
- se păstrează doar dacă a durat cel puțin 10 minute, temperatura a crescut,
  nu a fost deschisă nicio fereastră și e sezonul rece (nu modul Oprit sau
  Vară, nu în afara sezonului);
- o repornire a Home Assistant nu îl termină: episodul în curs se salvează și
  continuă dacă după repornire camera încă încălzește. Dacă nu mai încălzește,
  se renunță la el, pentru că nu se știe când s-a oprit încălzirea.

Pentru fiecare episod se notează cu câte grade a urcat camera, în câte minute
și temperatura medie de afară.

Din episoade se calculează o formulă simplă:

```
minute = parte fixă + grade × minute pe grad
```

- **Partea fixă**: minutele până începe camera să urce (pornește centrala, se
  încălzesc apa și caloriferele). E la fel pentru o urcare mică și pentru una
  mare.
- **Minutele pe grad**: cât durează fiecare grad. Depind de temperatura de
  afară: când e mai frig, de obicei durează mai mult.

**Exemplu** (valori presupuse pentru exemplu): partea fixă 25 de minute, iar la
5 °C afară camera are nevoie de 50 de minute pe grad. Pentru o urcare de la 18
la 21 °C (3 grade): 25 + 3 × 50 = **175 de minute**, deci aproape 3 ore.

**Ce se păstrează.** Ultimele 25 de episoade mici (sub 1 °C) și ultimele 25
mari (1 °C sau mai mult), separat, ca ciclurile mici și dese ale termostatului
să nu scoată din memorie urcările mari de dimineață. Numerele se recalculează
după fiecare episod, cu metoda celor mai mici pătrate (alegerea numerelor care
se potrivesc cel mai bine tuturor episoadelor).

**Până la primul episod** se folosește o valoare sigură: 60 de minute pe grad,
fără parte fixă. În card apare *se învață…* și dedesubt *implicit 60 min/1°C*.

**Cât durează învățarea.** Câteva zile. Cu cât sunt mai multe dimineți cu urcări
mari (de exemplu după `sleep`), cu atât învață mai repede partea fixă.

## Pornirea anticipată, pas cu pas

Pentru următoarea schimbare spre un nivel **mai cald**:

1. **Câte grade**: nivelul următor minus temperatura camerei acum.
2. **Ce temperatură va fi afară**: cu o entitate meteo cu prognoză orară, media
   prognozei între pornire și ora schimbării; altfel temperatura de afară de
   acum. Fiindcă pornirea depinde de temperatură și invers, calculul se face de
   3 ori.
3. **Câte minute**: formula de mai sus.
4. **Limita**: niciodată mai devreme decât *Anticipare maximă* (implicit 120 de
   minute).
5. Odată pornită, continuă până la ora schimbării, chiar dacă camera e caldă
   mai devreme. Regulile de mai sus de program (fereastră, prezență…) o pot
   întrerupe.

**Exemplu** (valori alese, cu partea fixă 25 de minute și 50 de minute pe grad
la 5 °C prognozate): dormitorul are 19,5 °C, `home` 22 °C la 07:00. Grade:
22 − 19,5 = 2,5. Minute: 25 + 2,5 × 50 = 150. Cu limita implicită de 120 de
minute pornirea e la 07:00 − 120 = **05:00** (fără limită ar fi fost 04:30).

Integrarea se trezește exact la momentul calculat al pornirii, nu doar la
verificarea periodică.

**Atenție la așteptări care nu se învață.** Minutele învățate încep când camera
chiar încălzește. Timpul în care camera cere căldură dar sursa așteaptă (timpul
minim oprit, *Camere necesare pentru pornirea sursei* mai mare de 1, camera de
referință) nu intră în învățare. Cu astfel de așteptări, pornirea anticipată
poate ajunge mai târziu la țintă.

## Cum învață o cameră să se răcească

Când camera nu mai cere căldură, se răcește. Integrarea măsoară și asta:
**episodul de răcire** ține de la sfârșitul unei cereri de căldură până la
următoarea și se păstrează dacă a durat cel puțin 10 minute, temperatura a
scăzut și nicio fereastră nu a fost deschisă.

O cameră pierde căldură cu atât mai repede cu cât e mai caldă decât afară. Din
fiecare episod se calculează un **coeficient**, iar camera păstrează media
ultimelor 30.

**Exemplu** (valori alese): coeficientul 0,0345 pe oră. La 21 °C în cameră și
0 °C afară, camera pierde 21 × 0,0345 = 0,72 °C pe oră; la 10 °C afară,
(21 − 10) × 0,0345 = 0,38 °C pe oră.

## Oprirea anticipată, pas cu pas

Înaintea unei schimbări spre un nivel **mai rece**:

1. **Confortul** nivelului curent: nivelul minus *toleranță*. Toleranța e
   `cold_tolerance` la Generic Thermostat, histerezisul la relee și termostatele
   fără `hvac_action`, *Toleranța opririi anticipate* la celelalte termostate.
2. **Cât poate sta camera fără căldură** până coboară la confort, după
   coeficientul învățat și temperatura de afară așteptată (prognoza din
   perioada opririi, în 3 treceri).
3. **Limita**: niciodată mai devreme decât *Oprire anticipată maximă* (implicit
   30 de minute). Până se învață răcirea, nivelul mai rece începe exact atât de
   devreme.
4. Odată începută, continuă până la ora schimbării. Dacă totuși camera coboară
   sub confort (s-a răcit mai repede decât a învățat), oprirea se **anulează**:
   nivelul curent revine până la ora schimbării. Dacă se întâmplă des, micșorează
   *Oprire anticipată maximă*.

**Exemplu** (valori alese): `home` 22 °C până la 22:00, toleranța 0,5 °C,
confortul deci 21,5 °C. Dacă după cele învățate camera scade de la 22 la
21,5 °C în 40 de minute, `sleep` începe la 22:00 − 40 = **21:20**. Cu limita
implicită de 30 de minute, începe la **21:30**.

## Ce vezi în card și în senzori

- **Timpul până la țintă**: cât timp camera e sub țintă, sub temperatura țintă
  apare de exemplu *~35 min* (atributul `time_to_target` al senzorului
  *Decizie*).
- **Următoarea pornire / oprire anticipată**, în *Detaliile* camerei, de exemplu
  *Pornire pentru presetul home (21.0°) la 07:00: începe pe la 05:10, afară
  prognozat 2.4°*; după ce a început, *în curs din …*.
- **Temperatura estimată la schimbare**, în timpul unei opriri anticipate, de
  exemplu *~21.5° la 22:00* (atributul `stop_forecast`).
- În grafic, următoarea pornire / oprire anticipată e o perioadă umbrită.
- **Învățarea**, în *Detalii*: numărul de episoade, partea fixă și minutele pe
  grad acum (de exemplu *12 episoade · 25 min + 49 min/°C acum*), cât de repede
  scade camera acum și ultimul episod.
- Senzorii **Viteză de încălzire** (minute pe grad acum, cu atribute) și **Cooling
  rate** (cât de repede scade camera acum fără încălzire).

## Resetarea învățării

Dacă ai schimbat ceva important (alte calorifere, altă curbă a centralei,
izolație nouă), învățarea se adaptează singură în câteva săptămâni. Ca să
înceapă imediat de la zero, apasă **Resetează învățarea încălzirii** sau **Reset
cooling learning** (butoanele camerei, sau *Resetează* în *Detaliile* cardului,
cu un al doilea clic pentru confirmare).

## Când nu se recomandă

Cu **TRV-uri** și o centrală pornită de un termostat care **nu e în Home
Assistant**, integrarea nu poate ști când merge centrala. Învățarea nu e sigură,
deci pornirea și oprirea anticipată nu sunt recomandate. Soluția e să pui
centrala (sau releul ei) în Home Assistant și să o alegi ca *Sursa de căldură*
(vezi [capitolul 8](08-sursa-si-energie.ro.md)).
