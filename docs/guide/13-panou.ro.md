# 13. Panoul SHC

*[English](13-panel.md) · [Cuprins](README.ro.md)*

Pe lângă card, integrarea adaugă o pagină proprie în bara laterală a Home
Assistant: **SHC**. Arată toată casa pe un singur ecran și adaugă ce nu încape
într-un card: programul tuturor camerelor alături, statistici și istoricul
deciziilor și al alertelor.

Panoul nu cere nicio setare. Apare odată cu prima casă și dispare când se
șterge ultima casă. Îl văd toți utilizatorii Home Assistant, nu doar
administratorii. Este desenat de același cod ca și cardul, așa că o cameră
arată și funcționează la fel în amândouă: ce spune [capitolul 10](10-card.ro.md)
despre o cameră este valabil și aici.

Panoul are cinci taburi: **Camere**, **Program**, **Statistici**,
**Istoric** și **Dispozitive**. Ultimul tab folosit se
păstrează în browser, iar tabul arătat este în adresă (`#week`, `#stats`,
`#history`, `#devices`), așa că un link (într-un dashboard, pe o tabletă)
deschide panoul direct pe el. Bara de sus arată numele casei (cu mai multe case,
numele integrării).

De la tastatură, săgețile trec de la o cameră la alta în listă (Home și End:
prima și ultima) și de la un tab la altul; locul pe care este tastatura este
conturat.

## Camere

Sus este casa (prezența, modul, pauza, oaspeții, vacanța, temperatura de afară
și încălzirea), pe margine sunt camerele, iar camera aleasă (marcată în listă
cu o bară în culoarea de accent a temei) este deschisă la mijloc, cu tot ce
arată și face cardul.

- O atingere pe o cameră din listă o deschide, cu o estompare scurtă. Camera se păstrează în adresă
  (`/shc#<cameră>`), așa că un link sau un semn de carte deschide acea cameră,
  și în browser.
- Pe telefon camerele sunt o listă; o cameră se deschide pe tot ecranul, cu
  **Înapoi** în bara de sus.

Pe un ecran lat:

- **Casa este o bară**: numele, prezența și persoanele, apoi temperatura de
  afară, sezonul de încălzire, cererea de căldură și timpul de încălzire (o
  atingere îi schimbă perioada). Dedesubt: modul, sursa de căldură,
  scenariile și butoanele Pauză, Oaspeți, Vacanță, Reevaluează și Automat.
- **Camera aleasă** are în stânga arcul, motivul, ce urmează și butoanele, iar
  în dreapta graficul, mai lat, deschis de la început (când panoul nu este destul de
  lat pentru amândouă, graficul trece sub cameră). Dedesubt: bara programului
  de azi și temperaturile nivelurilor (*Eco 18°*), cu nivelul curent conturat;
  secțiunile deschise de butoane (program, niveluri, detalii) vin după ele.

Pe telefon casa și camera sunt ca în card; graficul se deschide în fereastra
lui.

### Grupuri de camere

Lângă taburi, camerele se pot grupa **pe etaje** (etajul zonei din Home
Assistant în care este camera, în ordinea nivelurilor etajelor) sau **pe
circuite** (circuitul de încălzire al camerei, vezi
[capitolul 8](08-sursa-si-energie.ro.md)); camerele fără etaj sau
fără circuit sunt la sfârșit. Alegerea apare doar când o cameră are etaj sau
circuit și se păstrează în browser. Grupurile se folosesc în lista camerelor,
în tabul Program și în tabul Dispozitive.

### Mai multe case

Cu mai multe case, fiecare tab arată camerele fiecărei case sub numele ei,
așa că două camere cu același nume (un *Dormitor* în fiecare casă) se
deosebesc. În Istoric o cameră este scrisă cu casa ei (*Cabana · Dormitor*),
iar filtrul camerelor le arată sub casa lor.

## Program

Azi și următoarele 6 zile, așa cum le va rula programul: toate camerele în
ziua aleasă, cu nivelurile lor și temperaturile lor (*Eco 18°*, temperatura
lăsată deoparte când nu încape) pe o axă comună de la 00:00 la 24:00.

- Zilele se aleg deasupra barelor, fiecare cu data ei; ziua de azi este prima
  și este marcată. Azi, o linie arată ora curentă.
- Deasupra barelor, ce are ziua deosebit:
  - o **sărbătoare**: o zi lucrătoare pe care integrarea Workday (*senzorul
    Workday* al casei, vezi [capitolul 4](04-program.ro.md)) o arată liberă,
    rulată cu profilul zilelor de weekend; sau o zi de weekend care este
    lucrătoare;
  - un **profil din calendar**: un eveniment din calendar cu numele unui
    profil îl alege pentru ziua aceea;
  - un **nivel din calendar**: un eveniment din calendar cu numele unui nivel
    pune acel nivel pe orele lui; apare peste bare, hașurat;
  - **vacanța** programată a casei, cu începutul și sfârșitul ei; apare peste
    bare, hașurată, până când încălzirea pornește din nou înaintea sfârșitului
    ei; cât timp modul oaspeți este pornit vacanța este oprită, așa că doar
    este menționată.
- Lângă fiecare bară este numele profilului folosit în ziua aceea
  (*calendar* când l-a ales un eveniment din calendar).
- O cameră fără profil activ în ziua aceea arată *Niciun profil activ:
  protecție la îngheț*.
- O cameră care urmează un helper Schedule arată că programul ei se editează
  în helper.
- O atingere pe o cameră o deschide în tabul Camere, cu editorul programului
  deschis.
- Butonul de copiere de la capătul unui rând (arătat când mouse-ul este pe
  rând, mereu pe un ecran tactil) deschide camera cu *Copiază în alte camere*: tot programul ei se copiază în camerele alese (vezi
  [capitolul 10](10-card.ro.md)).

Zilele sunt calculate de integrare la fel cum le calculează camerele, cu
începutul zilei de program al casei, și sunt arătate în fusul orar al casei
(în ziua în care se schimbă ora, orele cad unde sunt de fapt). Se citesc din
nou imediat ce se schimbă un program, vacanța sau modul oaspeți. Ce nu se poate ști dinainte nu apare:
prezența (acasă sau plecat), ferestrele deschise, schimbările manuale și modul
casei schimbat de mână. Sărbătorile și evenimentele din calendar se citesc
pentru azi și următoarele 7 zile, la fiecare oră.

## Statistici

Timpul de încălzire și temperaturile casei și ale fiecărei camere, pe **zile**,
**săptămâni** sau **luni**: ultimele 14 zile, 12 săptămâni sau 12 luni. Vin din
statisticile pe termen lung ale Home Assistant (recorderul), deci se păstrează
cât timp le păstrează Home Assistant. Barele cresc de la bază când se arată o
perioadă (nu și cu *mișcare redusă*).

- **Casa**: o bară pentru fiecare zi, săptămână sau lună, cu timpul de
  încălzire, iar peste bare o linie cu media temperaturii de afară în fiecare
  perioadă, pe o scară proprie (valoarea ei cea mai mare, cea din mijloc și
  cea mai mică, în dreapta barelor), ca perioadele mai reci și încălzirea mai lungă să se vadă
  împreună. O atingere pe un punct al liniei arată media perioadei, cu
  valoarea cea mai mică și cea mai mare; o nouă atingere le ascunde. Titlul dă
  timpul total și media de afară, cu valoarea cea mai mică și cea mai mare.
- **O atingere pe o bară** alege perioada aceea: sub bare apar timpul casei,
  temperatura de afară (media, minimul și maximul) și numărul de porniri
  cerute; camerele de dedesubt arată atunci doar perioada aceea. O nouă
  atingere pe aceeași bară, sau pe ✕, arată din nou tot intervalul.
- **La același frig**: sub bare, ultima perioadă întreagă (sau cea aleasă)
  față de cea dinainte, ca ore de încălzire pe grad între ținta medie a
  camerelor și media de afară (de exemplu *joi, 26 noiembrie: −8% față de
  miercuri, 25 noiembrie, la același frig*; orele pe grad ale amândurora la
  trecerea cu mouse-ul). O perioadă mai rece cere mai multă încălzire; asta o
  scoate din calcul, așa că rămân casa și programul ei (și soarele, vântul,
  cine a fost acasă). Nimic pentru perioada de acum (încă neîntreagă), fără
  senzor de afară sau când afară n-a fost mai frig decât țintele.
- **Ce a făcut SHC**: orele în care casa a fost ținută sub program de fiecare
  regulă în intervalul arătat (sau în perioada aleasă): plecați (și vacanță
  sau departe), camere goale, oprirea anticipată și fereastră deschisă,
  fiecare numărată cât cel puțin o cameră a fost sub ea (timpul casei, nu
  adunat pe camere). Vin din senzorii casei *Timp plecați* și ceilalți,
  numărați de la versiunea 2.7.1.
- **Camerele**: fiecare cameră cu timpul ei de încălzire, partea ei din timpul
  tuturor camerelor, temperatura medie și ținta medie (minimul și maximul la
  trecerea cu mouse-ul), în ordinea timpului.
- **De câte ori a fost cerută pornirea sursei de căldură**, pe zile. Acestea
  vin din istoricul Home Assistant, păstrat implicit 10 zile: zilele mai vechi
  nu au bară.
- **Pornirea anticipată**: pentru fiecare cameră care o are, cum s-au încheiat
  pornirile în perioada arătată (sau în cea aleasă): temperatura nivelului
  atinsă **la timp** (și cu câte minute înainte de ora nivelului, în medie),
  **întârziat** (cu câte minute după ea, în medie) sau **neatinsă** cât a ținut
  nivelul. Se numără doar pornirile care au mers până la ora nivelului: una
  oprită înainte (a plecat cineva, o fereastră, o schimbare manuală) nu a avut
  ocazia să încerce. Integrarea păstrează ultimele 100 ale fiecărei camere, și
  după repornire.

- **Încălzirea pe ore**: dedesubt, un rând de 24 de ore pentru fiecare cameră,
  cu atât mai închis la culoare cu cât camera a fost încălzită mai multe
  minute în ora aceea, în ultimele 7 zile: ca medie a celor 7 zile (când
  încălzește de obicei o cameră) sau pentru una dintre ele. Vine din istoricul
  Home Assistant (cererea de căldură a fiecărei camere cât timp sursa de
  căldură a funcționat), deci are nevoie ca zilele acelea să fie în istoric
  (implicit 10); orele sunt cele din fusul orar al casei. O atingere pe o oră
  îi arată minutele sub grilă; ✕ le ascunde.

Cât timp tabul este deschis, statisticile se cer din nou la fiecare 5 minute.

## Istoric

- **Alerte acum**, sus: fiecare alertă activă, din toate casele, o singură
  dată, cu camera ei (sau *Toată casa*) și de când este activă. Când alerta
  numește o entitate (un termostat, un senzor), o atingere pe textul ei
  deschide acea entitate; **Deschide camera** deschide camera ei. Numărul
  alertelor active apare și pe tabul Istoric.
- Dedesubt, **istoricul**: deciziile fiecărei camere și alertele, cu începutul
  și sfârșitul lor, cele mai noi primele, pe zile. Se pot arăta doar deciziile
  sau doar alertele, și o cameră sau toate (o cameră arată alertele ei și pe
  cele ale întregii case).

Integrarea păstrează ultimele 100 de decizii ale fiecărei camere și ultimele
100 de alerte ale fiecărei case, și după reporniri. O alertă încă activă când
Home Assistant se oprește se încheie la repornire și este anunțată din nou
după aceea, dacă încă este valabilă.

## Dispozitive

### Umiditate

Sus, când o cameră are senzor de umiditate: umiditatea aerului fiecărei
astfel de camere și cea estimată la peretele ei cel mai rece (din temperatura
de afară), cele cu risc de mucegai primele. O cameră are risc cu o alertă de
mucegai activă sau cu 80% ori mai mult la peretele cel mai rece, ca în
Detaliile ei. Numărul camerelor cu risc apare în titlu; o atingere pe o cameră
îi deschide Detaliile.

### Dispozitivele

Toate entitățile folosite de camere, din toate casele, într-o singură listă:
termostate, TRV-uri, relee, senzori de temperatură și umiditate, ferestre,
senzori de prezență și entități de calibrare. O entitate folosită de mai multe
camere (o fereastră comună a două camere) apare o singură dată, cu toate
camerele ei.

- Primele sunt cele **indisponibile** (numărul lor apare în titlu), apoi cele
  a căror baterie Home Assistant o raportează descărcată, apoi restul, pe
  camere.
- Fiecare rând arată numele, rolul și camera, starea de acum (la un termostat
  temperatura, ținta și dacă încălzește), **bateria** și de cât timp s-a
  schimbat ultima dată entitatea.
- Bateria este a dispozitivului entității din Home Assistant: un senzor de
  baterie în % sau un senzor binar *battery* (*descărcată*). O entitate al
  cărei dispozitiv nu are entitate de baterie nu arată nimic. Nu cere nicio
  setare.
- O atingere pe un rând deschide entitatea.
