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

Panoul are patru taburi: **Camere**, **Program**, **Statistici** și
**Istoric**. Ultimul tab folosit se păstrează în browser.

## Camere

Sus este casa (prezența, modul, pauza, oaspeții, vacanța, temperatura de afară
și încălzirea), pe margine sunt camerele, iar camera aleasă este deschisă la
mijloc, cu tot ce arată și face cardul.

- O atingere pe o cameră din listă o deschide. Camera se păstrează în adresă
  (`/shc#<cameră>`), așa că un link sau un semn de carte deschide acea cameră,
  și în browser.
- Pe telefon camerele sunt o listă; o cameră se deschide pe tot ecranul, cu
  **Înapoi** în bara de sus.

## Program

Toate camerele într-o zi, cu bara profilului pe care îl folosește fiecare
cameră în ziua aceea, pe o axă comună de la 00:00 la 24:00.

- Ziua se alege deasupra barelor; ziua de azi este marcată și se deschide
  prima. Azi, o linie arată ora curentă.
- Lângă fiecare bară este numele profilului folosit în ziua aceea.
- O cameră fără profil activ în ziua aceea arată *Niciun profil activ:
  protecție la îngheț*: într-o asemenea zi camera păstrează protecția la
  îngheț (vezi [capitolul 4](04-program.ro.md)).
- O cameră care urmează un helper Schedule arată că programul ei se editează
  în helper.
- O atingere pe o cameră o deschide în tabul Camere, cu editorul programului
  deschis.

Profilul unei zile se alege la fel ca în integrare: un profil al acelei zile
din săptămână, altfel cel al zilelor lucrătoare sau al zilelor de weekend,
altfel cel al tuturor zilelor. Aici zilele lucrătoare sunt de luni până
vineri: zilele libere dintr-un calendar și profilele alese de un eveniment din
calendar nu apar în acest tab (programul camerei și graficul ei arată ziua așa
cum este de fapt).

## Statistici

Timpul de încălzire și temperaturile casei și ale fiecărei camere, pe **zile**,
**săptămâni** sau **luni**: ultimele 14 zile, 12 săptămâni sau 12 luni. Vin din
statisticile pe termen lung ale Home Assistant (recorderul), deci se păstrează
cât timp le păstrează Home Assistant.

- **Casa**: o bară pentru fiecare zi, săptămână sau lună, cu timpul de
  încălzire, iar sub fiecare bară media temperaturii de afară în perioada
  aceea. Titlul dă timpul total și media de afară, cu valoarea cea mai mică și
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
- **Ce a învățat SHC**: toate camerele alături, cu valorile din Detaliile lor
  (vezi [capitolul 7](07-anticipare-si-invatare.ro.md)): starea învățării cu
  eroarea obișnuită, încălzirea, inerția, pierderea de căldură și curba de
  vreme. O cameră care încă învață arată câte ore cu și fără încălzire a văzut
  din orele de care are nevoie. O atingere pe o cameră o deschide, cu
  Detaliile ei.

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
