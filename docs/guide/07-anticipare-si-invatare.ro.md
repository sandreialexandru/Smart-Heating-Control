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
încălzire, și învață patru numere:

- **Încălzirea**: câte °C pe oră adaugă încălzirea când dă toată căldura.
- **Curba de temperatură**: cu cât dă încălzirea mai mult (sau mai puțin) când
  e mai frig afară. O centrală cu compensare după exterior încălzește apa mai
  tare la frig; o pompă de căldură poate da mai puțin; o temperatură fixă a
  apei sau un radiator electric dă la fel, iar curba se învață 0.
- **Pierderea de căldură**: cât de repede se răcește camera, proporțional cu
  cât e mai caldă decât afară (cu cât e mai frig afară, cu atât mai repede).
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
robinetelor sau în afara sezonului rece (modul Oprit sau Vară, în afara
sezonului).

**Până se învață** (4 ore cu încălzire și 4 ore fără, de obicei în prima zi) se
folosește o valoare sigură: 60 de minute pe grad, fără inerție. În card apare
*se învață… 2 din 4 h cu încălzire, 1 din 4 h fără* și dedesubt *implicit
60 min/1°C*.

**Fără temperatură de afară** în casă, pierderea de căldură se învață ca un
număr constant de grade pe oră, iar curba de temperatură nu se învață.

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
minim oprit, *Camere necesare pentru pornirea sursei* mai mare de 1, camera de
referință) nu intră în învățare. Cu astfel de așteptări, pornirea anticipată
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
  *45 min/°C acum · inerție 30 min*) sau progresul în timpul învățării, și cât
  de repede scade camera acum fără încălzire.
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
