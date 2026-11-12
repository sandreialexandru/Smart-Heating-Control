# 7. Pornirea și oprirea anticipată, învățarea

*[English](07-optimal-start-stop-and-learning.md) · [Cuprins](README.ro.md)*

Capitolul explică pe înțelesul tuturor cum învață fiecare cameră și cum
folosește ce a învățat. Calculele complete, cu exemple și simulări,
sunt în [Cum învață integrarea](../learning.ro.md).

## De ce e nevoie de anticipare

Programul spune „`home` 21 °C de la 07:00”. Fără anticipare, încălzirea
pornește la 07:00 și camera e caldă abia pe la 08:30. Cu **pornirea
anticipată**, integrarea pornește încălzirea mai devreme, ca la 07:00 camera să
fie deja la 21 °C.

Invers, programul spune „`sleep` 18 °C de la 22:00”. Camera e caldă și s-ar
răci oricum încet. Cu **oprirea anticipată**, nivelul mai rece începe puțin mai
devreme, cât timp camera rămâne confortabilă până la 22:00. Se economisește
energie fără ca diferența să se simtă.

Ambele se pornesc pe cameră, la pasul *Program*
([capitolul 3](03-camere.ro.md#pasul-7-program)). Oprirea anticipată are nevoie
de o temperatură de afară (senzor sau entitate meteo).

## Cum învață o cameră

Nu trebuie introdus nimic despre casă (calorifere, izolație, centrală,
încălzire în pardoseală). Camera **se urmărește singură** tot timpul, cu și fără
încălzire, și învață cinci numere:

- **Încălzirea**: câte °C pe oră adaugă încălzirea când dă toată căldura.
- **Curba de temperatură**: cu cât dă încălzirea mai mult (sau mai puțin) când
  e mai frig afară. O centrală cu compensare după exterior încălzește apa mai
  tare la frig; o pompă de căldură poate da mai puțin; o temperatură fixă a
  apei sau un radiator electric dă la fel, iar curba se învață 0.
- **Pierderea de căldură**: cât de repede se răcește camera, proporțional cu
  cât e mai caldă decât afară (cu cât e mai frig afară, cu atât mai repede).
- **Soarele**: câte °C pe oră adaugă soarele. Se învață doar cu o entitate meteo
  (de la ea se știu norii) și doar când se vede clar; altfel e 0. Înălțimea
  soarelui se calculează din oră și din locația din Home Assistant, deci
  orientarea ferestrelor nu trebuie dată.
- **Inerția**: cât de încet reacționează încălzirea. După pornire se încălzesc
  întâi centrala, apa și caloriferele (sau pardoseala); după oprire, ele mai dau
  căldură o vreme. Calorifere: de obicei 10 – 30 de minute; încălzire în
  pardoseală: ore. Nu se setează nimic: se învață.

**Exemplu** (valori presupuse pentru exemplu): încălzire 2 °C pe oră, fără
curbă de temperatură, pierdere
0,05 pe oră pentru fiecare grad de diferență, inerție 30 de minute. La 19 °C în
cameră și 5 °C afară, camera pierde 0,05 × (19 − 5) = 0,7 °C pe oră, deci cu
încălzirea complet pornită urcă 2 − 0,7 = 1,3 °C pe oră. De la 18 la 21 °C,
pornind la rece, la 5 °C afară are nevoie de **186 de minute**, circa 3 ore
(calculat minut cu minut, cu inerția).

**Cum învață.** La fiecare 30 de minute camera notează cât a urcat sau a
coborât, dacă a încălzit și diferența față de afară. Numerele sunt cele care se
potrivesc cel mai bine tuturor acestor măsurători (metoda celor mai mici
pătrate). Măsurătorile mai vechi contează mai puțin (pe jumătate după o
săptămână), deci învățarea urmează singură camera când se schimbă ceva. O
măsurătoare departe de ce face camera de obicei (o ușă lăsată deschisă,
gătitul) contează mai puțin. Nu se folosesc: măsurătorile cu o fereastră
deschisă, cu starea sursei de căldură necunoscută, în timpul exercițiului
robinetelor, cât TRV-urile sunt ținute deschise pentru sursa de căldură (*Ține
deschis ultimul TRV*) sau camera e încălzită la ocazie cât merge centrala, ori în afara sezonului rece (modul Oprit sau Vară, în afara
sezonului).

**Până se învață** (4 ore cu încălzire și 4 ore fără, de obicei în prima zi) se
folosește o valoare sigură: 60 de minute pe grad, fără inerție. În card apare
*se învață…* cu două bare, *cu încălzire 2 din 4 h* și *fără încălzire 1 din
4 h*, iar dedesubt *implicit 60 min/1°C*.

**Fără temperatură de afară** în casă, pierderea de căldură se învață ca un
număr constant de grade pe oră, iar curba de temperatură nu se învață.

**Soarele în predicții.** După ce s-a învățat, pornirea și oprirea anticipată,
timpul până la țintă și temperatura prezisă din card socotesc soarele: înălțimea
lui la acea oră și norii din prognoza orară (altfel norii de acum). Exemplu
(camera de mai sus, soare învățat 1,5 °C/h, un semnal solar de 0,3, adică
1,5 × 0,3 = 0,45 °C/h, afară 0 °C): de la 18 la 21 °C are nevoie de 161 de
minute în loc de 231. Setarea *Câștig solar* a camerei e separată și rămâne:
ea coboară ținta cât e soare. Detalii în
[Cum învață integrarea](../learning.ro.md#10-soarele).

## Pornirea anticipată, pas cu pas

Pentru următoarea schimbare spre un nivel **mai cald**:

1. **Câte grade**: nivelul următor minus temperatura camerei acum.
2. **Ce temperatură va fi afară**: cu o entitate meteo cu prognoză orară, media
   prognozei între pornire și ora schimbării; altfel temperatura de afară de
   acum. Fiindcă pornirea depinde de temperatură și invers, calculul se face de
   3 ori.
3. **Câte minute**: camera se simulează minut cu minut cu încălzirea pornită,
   de la temperatura ei de acum și de cât de calde îi sunt deja caloriferele
   (inerția).
4. **Limita**: niciodată mai devreme decât *Anticipare maximă* (implicit 120 de
   minute).
5. Odată pornită, continuă până la ora schimbării, chiar dacă camera e caldă
   mai devreme. Regulile de mai sus de program (fereastră, prezență…) o pot
   întrerupe.

**Exemplu** (camera din exemplul de mai sus, 5 °C prognozate): dormitorul are
18 °C, `home` 21 °C la 07:00. Minute: 186. Cu limita implicită de 120 de minute
pornirea e la 07:00 − 120 = **05:00** (fără limită ar fi fost la 07:00 − 186 de
minute = 03:54).

Integrarea se trezește exact la momentul calculat al pornirii, nu doar la
verificarea periodică.

**Atenție la așteptări care nu se învață.** Minutele învățate încep când camera
chiar încălzește. Timpul în care camera cere căldură dar sursa așteaptă (timpul
minim oprit, *Camere necesare pentru pornirea sursei* mai mare de 1, o cameră
secundară care așteaptă altă cameră) nu intră în învățare. Cu astfel de așteptări, pornirea anticipată
poate ajunge mai târziu la țintă.

## Oprirea anticipată, pas cu pas

Înaintea unei schimbări spre un nivel **mai rece**:

1. **Confortul** nivelului curent: nivelul minus *toleranță*. Toleranța e
   `cold_tolerance` la Generic Thermostat, histerezisul la relee și termostatele
   fără `hvac_action`, *Toleranța opririi anticipate* la celelalte termostate.
2. **Cât poate sta camera fără căldură** până coboară la confort, simulat cu
   pierderea de căldură învățată, inerția (caloriferele calde încă dau căldură)
   și temperatura de afară așteptată (prognoza din perioada opririi, în 3
   treceri).
3. **Limita**: niciodată mai devreme decât *Oprire anticipată maximă* (implicit
   30 de minute). Până se învață răcirea, nivelul mai rece începe exact atât de
   devreme.
4. Odată începută, continuă până la ora schimbării. Dacă totuși camera coboară
   sub confort (s-a răcit mai repede decât a învățat), oprirea se **anulează**:
   nivelul curent revine până la ora schimbării. Dacă se întâmplă des, *Oprire
   anticipată maximă* trebuie micșorată.

**Exemplu** (valori alese): `home` 22 °C până la 22:00, toleranța 0,5 °C,
confortul deci 21,5 °C. Dacă după cele învățate camera scade de la 22 la
21,5 °C în 40 de minute, `sleep` începe la 22:00 − 40 = **21:20**. Cu limita
implicită de 30 de minute, începe la **21:30**.

## Pornirea și oprirea după inerție

Doar pentru camerele pe care integrarea le pornește și le oprește singură: un
releu, un termostat comandat *Pornit / oprit (hvac mode)* sau TRV-uri cu
*Încălzește după senzorul camerei* (mai jos). Histerezisul ține
camera într-o bandă, de exemplu 20,7 – 21,3 °C în jurul a 21 °C. Fără altceva,
încălzirea se oprește la 21,3 °C, iar caloriferele, încă fierbinți, duc camera
mai sus; pornește din nou la 20,7 °C, iar camera mai coboară până se încălzesc
caloriferele.

Cu **Folosește inerția învățată** (implicit pornit, la pasul *Comandă pornit /
oprit*), după ce camera și-a învățat modelul:

- încălzirea **se oprește** imediat ce căldura aflată încă pe drum ar duce
  singură camera la limita de sus a benzii;
- **pornește** imediat ce camera ar coborî la limita de jos a benzii înainte să
  ajungă căldura.

Banda rămâne limita: la 21,3 °C se oprește mereu, la 20,7 °C pornește mereu, iar
timpii minimi pornit / oprit se respectă în continuare. Cât e oprită mai
devreme și camera e sub țintă, cardul arată *oprită mai devreme: căldura deja
dată duce camera la ~21,3°*.

**Exemplu** (valori presupuse: calorifere din fontă care adaugă 2 °C pe oră,
inerție 60 de minute, ținta 21 °C): doar cu banda, încălzirea se oprește la
21,3 °C, iar camera ajunge la circa 21,6 °C; cu inerția învățată se oprește pe
la 21,1 °C, iar camera ajunge la circa 21,3 °C.

Simulare (camere fictive, nu măsurători): încălzirea h și pierderea k ale
fiecărei camere ca mai jos, temperatura de afară aleatoare între −5 și 10 °C în
fiecare zi, cu ±3 °C între zi și noapte, 21 °C între 06:00 și 23:00 și 18,5 °C
noaptea, senzorul rotunjit la 0,1 °C, mici perturbări aleatoare, învățat de la
început cu codul integrării; zilele 5 – 20 între 08:00 și 23:00, trei rulări cu
vreme diferită. Calorifere 20 min: h 2,5 °C/h, k 0,06; 30 și 60 min: h 2,
k 0,05; pardoseală: h 1,6, k 0,04.

| Cameră (releu, histerezis 0,3 °C) | Distanța medie față de țintă, doar banda → cu inerția | Timp la peste 0,5 °C deasupra / sub țintă, doar banda → cu inerția | Porniri pe oră |
|---|---|---|---|
| Calorifere, inerție 20 min | 0,24 → 0,19 – 0,20 °C | 0,3 – 0,8 % / 0,7 – 1,1 % → 0 / 0 – 0,2 % | 0,45 → 0,50 |
| Calorifere, inerție 30 min | 0,26 → 0,21 °C | 2,0 – 2,4 % / 2,4 – 2,9 % → 0 / 1,8 – 2,1 % | 0,31 → 0,36 |
| Fontă, inerție 60 min | 0,33 – 0,34 → 0,27 °C | 13,7 – 14,7 % / 3,8 – 4,6 % → 0 / 6,3 – 6,8 % | 0,20 → 0,26 |
| Încălzire în pardoseală, inerție 180 min | 0,90 – 0,92 → 0,44 – 0,47 °C | 31 – 34 % / 34 – 36 % → 7 – 9 % / 16 – 18 % | 0,07 → 0,6 |

Cu cât încălzirea e mai lentă, cu atât câștigul e mai mare: puțin la
caloriferele obișnuite, abaterea înjumătățită la încălzirea în pardoseală.
Încălzirea a mers la fel de mult sau mai puțin (pardoseală: 52 – 55 % din timp
→ 43 – 45 %), pentru că nu mai merge căldură peste bandă.

**TRV-uri încălzite după senzorul camerei** (*Încălzește după senzorul camerei*): senzorul
camerei decide cererea de căldură cu histerezisul, ca la un releu, deci inerția
învățată se aplică la fel. Într-o simulare cu TRV-uri care urmează după 3
minute (în rest aceleași ipoteze ca mai sus):

| Cameră (încălzire după senzorul camerei) | Distanța medie față de țintă, doar banda → cu inerția | Timp la peste 0,5 °C deasupra țintei | Porniri pe oră |
|---|---|---|---|
| Calorifere, inerție 20 min | 0,28 → 0,23 – 0,25 °C | 5,3 – 6,7 % → 0 – 0,3 % | 0,40 → 0,45 |
| Calorifere, inerție 30 min | 0,28 – 0,31 → 0,23 – 0,25 °C | 6,4 – 7,4 % → 0 – 0,1 % | 0,30 → 0,32 |
| Fontă, inerție 60 min | 0,36 → 0,30 – 0,31 °C | 17,9 – 20,1 % → 0 | 0,20 → 0,23 |

Timpul la peste 0,5 °C sub țintă a rămas cam la fel pentru calorifere
(1,0 – 4,3 % → 0,7 – 3,0 %) și a crescut pentru fontă (3,4 – 6,3 % →
7,3 – 8,0 %).

Termostatele și TRV-urile comandate prin *Temperatură* fără încălzirea după senzorul camerei, precum și
Generic Thermostat, se reglează singure: integrarea nu le pornește și oprește,
deci inerția învățată nu se aplică acolo.

## Ce arată cardul și senzorii

- **Timpul până la țintă**: cât timp camera e sub țintă, sub temperatura țintă
  apare de exemplu *~35 min* (atributul `time_to_target` al senzorului
  *Decizie*).
- **Următoarea pornire / oprire anticipată**, în *Detaliile* camerei, de exemplu
  *Pornire pentru presetul home (21.0°) la 07:00: începe pe la 05:10, afară
  prognozat 2.4°*; după ce a început, *în curs din …*.
- **Temperatura estimată la schimbare**, în timpul unei opriri anticipate, de
  exemplu *~21.5° la 22:00* (atributul `stop_forecast`).
- În grafic, următoarea pornire / oprire anticipată e o perioadă umbrită.
- **Învățarea**, în *Detalii*: minutele pe grad acum și inerția (de exemplu
  *45 min/°C acum · inerție 30 min*) sau progresul în timpul învățării, soarele
  învățat (doar dacă s-a văzut) și cât de repede scade camera acum fără
  încălzire.
- Senzorii **Viteză de încălzire** (minute pe grad acum, cu numerele învățate
  ca atribute) și **Viteză de răcire** (cât de repede scade camera acum fără
  încălzire).

## Resetarea învățării

După o schimbare importantă (alte calorifere, altă curbă a centralei, izolație
nouă), învățarea se adaptează singură în una – două săptămâni. Ca să înceapă imediat
de la zero, există butonul **Resetează învățarea** (butonul camerei, sau
*Resetează* în *Detaliile* cardului, cu un al doilea clic pentru confirmare);
camera învață din nou în circa o zi.

## Când nu se recomandă

Cu **TRV-uri** și o centrală pornită de un termostat care **nu e în Home
Assistant**, integrarea nu poate ști când merge centrala. Învățarea nu e sigură,
deci pornirea și oprirea anticipată nu sunt recomandate. Soluția e ca centrala
(sau releul ei) să fie adăugată în Home Assistant și aleasă ca *Sursa de
căldură* ([capitolul 8](08-sursa-si-energie.ro.md)).
