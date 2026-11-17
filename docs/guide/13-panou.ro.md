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
**Istoric** și **Dispozitive**. Ultimul tab folosit se păstrează în browser.

## Camere

Sus este casa (prezența, modul, pauza, oaspeții, vacanța, temperatura de afară
și încălzirea), pe margine sunt camerele, iar camera aleasă este deschisă la
mijloc, cu tot ce arată și face cardul.

- O atingere pe o cameră din listă o deschide. Camera se păstrează în adresă
  (`/shc#<cameră>`), așa că un link sau un semn de carte deschide acea cameră,
  și în browser.
- Pe telefon camerele sunt o listă; o cameră se deschide pe tot ecranul, cu
  **Înapoi** în bara de sus.

### Grupuri de camere

Lângă taburi, camerele se pot grupa **pe etaje** (etajul zonei din Home
Assistant în care este camera, în ordinea nivelurilor etajelor) sau **pe
circuite** (circuitul de încălzire al camerei, vezi
[capitolul 8](08-sursa-si-energie.ro.md)); camerele fără etaj sau
fără circuit sunt la sfârșit. Alegerea apare doar când o cameră are etaj sau
circuit și se păstrează în browser. Grupurile se folosesc în lista camerelor,
în tabul Program și în tabul Dispozitive.

## Program

Azi și următoarele 6 zile, așa cum le va rula programul: toate camerele în
ziua aleasă, cu nivelurile lor pe o axă comună de la 00:00 la 24:00.

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
- Butonul de copiere de la capătul unui rând deschide camera cu *Copiază în
  alte camere*: tot programul ei se copiază în camerele alese (vezi
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
cât timp le păstrează Home Assistant.

- **Casa**: o bară pentru fiecare zi, săptămână sau lună, cu timpul de
  încălzire, iar sub fiecare bară media temperaturii de afară în perioada
  aceea. Media de afară este desenată și ca o linie peste bare, pe o scară
  proprie (valoarea ei cea mai mare și cea mai mică sunt scrise în stânga),
  ca perioadele mai reci și încălzirea mai lungă să se vadă împreună. Titlul dă timpul total și media de afară, cu valoarea cea mai mică și
  cea mai mare.
- **O atingere pe o bară** alege perioada aceea: sub bare apar timpul casei,
  temperatura de afară (media, minimul și maximul) și numărul de porniri
  cerute; camerele de dedesubt arată atunci doar perioada aceea. O nouă
  atingere pe aceeași bară, sau pe ✕, arată din nou tot intervalul.
- **Camerele**: fiecare cameră cu timpul ei de încălzire, partea ei din timpul
  tuturor camerelor, temperatura medie și ținta medie (minimul și maximul la
  trecerea cu mouse-ul), în ordinea timpului.
- **De câte ori a fost cerută pornirea sursei de căldură**, pe zile. Acestea
  vin din istoricul Home Assistant, păstrat implicit 10 zile: zilele mai vechi
  nu au bară.

- **Încălzirea pe ore**: dedesubt, un rând de 24 de ore pentru fiecare cameră,
  cu atât mai închis la culoare cu cât camera a fost încălzită mai multe
  minute în ora aceea, în ultimele 7 zile: ca medie a celor 7 zile (când
  încălzește de obicei o cameră) sau pentru una dintre ele. Vine din istoricul
  Home Assistant (cererea de căldură a fiecărei camere cât timp sursa de
  căldură a funcționat), deci are nevoie ca zilele acelea să fie în istoric
  (implicit 10); orele sunt cele din fusul orar al casei.

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
