# 6. Vremea și sezonul

*[English](06-weather.md) · [Cuprins](README.ro.md)*

Vremea poate **opri** încălzirea (când e cald) sau o poate **ajusta** puțin
(când e foarte frig sau e soare). Nu poate ridica niciodată temperatura peste
ce cere programul, cu excepția compensării de câteva zecimi de grad, aleasă în
setări.

Toate setările sunt în opțiunile casei, la **Vreme și sezon**
([capitolul 2](02-instalare-si-casa.ro.md#vreme-și-sezon)). Fără senzor de afară
și fără entitate meteo, formularul nu permite pornirea funcțiilor care au
nevoie de ele.

## Temperatura de afară

Vine din *Senzor de temperatură exterioară* (care nu poate fi senzorul de
temperatură al unei camere; o valoare care nu e număr, `nan` sau `inf`, e
ignorată) sau, dacă nu există unul, din
temperatura *Entității meteo*.

Integrarea păstrează valorile din ultimele 48 de ore și calculează **media pe
ultimele *Medie pe* ore** (implicit 6), ponderată în timp: fiecare valoare
contează cât timp a fost valabilă.

*Medie pe* înseamnă și **cât rămâne valabilă o valoare**: dacă senzorul nu mai
trimite nimic atâtea ore, temperatura de afară devine **necunoscută**. Atunci nu
se aplică oprirea când e cald, compensarea și ignorarea ferestrelor, nu se
învață episoade și nu se face oprire anticipată, până când senzorul revine.
Dacă nicio sursă configurată nu dă temperatura (senzorul căzut și entitatea meteo
lipsă, indisponibilă sau fără temperatură) mai mult de *Alertă când un dispozitiv
e indisponibil mai mult de* (implicit 15 minute), apare o alertă. Cu senzorul
căzut și meteo bun nu apare nicio alertă: se folosește temperatura din meteo.

## Oprirea când e cald afară

*Oprește încălzirea când e cald afară* (oprit implicit). Folosește:

| Setare | Implicit | Rol |
| --- | --- | --- |
| Prag de oprire (exterior) | 18 °C | media la care încălzirea se oprește |
| Histerezis prag | 1 °C | încălzirea poate porni din nou abia la prag − histerezis |
| Medie pe | 6 h | pe câte ore se face media |

Cu valorile implicite: **încălzirea se oprește când media pe 6 ore ajunge la
18 °C** și **poate porni din nou când media coboară la 18 − 1 = 17 °C**. Între
17 și 18 °C rămâne cum era. Fără această bandă, o medie care oscilează în jurul
pragului ar porni și opri încălzirea de multe ori.

De ce o medie și nu temperatura de acum: o după-amiază însorită de 20 °C într-o
zi de octombrie nu înseamnă că seara nu va fi frig. Media pe 6 ore se mișcă
încet și ține cont de toată ziua.

**Exemplu** (valori alese). Toată dimineața au fost 14 °C, iar de la 12:00 sunt
22 °C. La 15:00, media pe ultimele 6 ore (09:00–15:00) e
(3 h × 14 + 3 h × 22) ÷ 6 h = (42 + 66) ÷ 6 = 18 °C: încălzirea se oprește.

Cât timp încălzirea e oprită de vreme, decizia camerei e *Cald afară: încălzire
oprită (ar fi …)*, iar cardul arată la casă *Cald afară: pornit • încălzirea e
oprită până media scade la 17°*.

## Prognoza

*Folosește prognoza* (oprit implicit) are nevoie de o **entitate meteo cu
prognoză orară** și de oprirea când e cald pornită. Folosește **media
prognozei pe următoarele *Ore de prognoză*** (implicit 3), niciodată o singură
oră. În medie, fiecare valoare din prognoză e valabilă pentru ora ei, iar până
la următoarea oră din prognoză se folosește temperatura măsurată acum.

Prognoza are două efecte:

**1. Încălzirea e oprită pentru că a fost cald, dar vine frigul.** Dacă media
prognozei e la **prag − histerezis sau sub** (cu valorile implicite 17 °C),
încălzirea poate porni din nou, chiar dacă media măsurată e încă mare. Așa o
după-amiază caldă nu ține încălzirea oprită într-o seară rece. Peste 17 °C
încălzirea rămâne oprită. Cardul arată *anulat (prognoză) • vine frigul: media
prognozei pe 3 h este …, camerele încălzesc la nevoie*.

**2. Încălzirea merge, dar vine căldura.** Dacă media prognozei ajunge **la
prag sau peste** (18 °C), încălzirea se oprește **mai devreme**, înainte ca
media măsurată să ajungă acolo. Rămâne oprită până când media prognozei coboară
la prag − histerezis (17 °C), cu același histerezis ca media măsurată; starea
se salvează și peste o repornire. Cardul arată *pornit (prognoză) • încălzirea
e oprită: media prognozei pe 3 h este …*.

**Cât de devreme se oprește.** Depinde de *Ore de prognoză* și de cât de cald
vine. Exemplu (valori alese): acum 10 °C, vine o perioadă de 20 °C, prag 18 °C,
3 ore de prognoză. Media ajunge la 18 °C când partea caldă e
(18 − 10) ÷ (20 − 10) = 0,8 din fereastră, adică încălzirea se oprește cu
3 h × (1 − 0,8) = 0,6 h = 36 de minute înainte de perioada caldă. Cu 6 ore de
prognoză ar fi 72 de minute. Mai multe ore înseamnă o oprire mai devreme.

Fără prognoză (sau când nu acoperă orele cerute) decide doar media măsurată.
Prognoza se citește la fiecare 30 de minute, iar decizia se recalculează
imediat după fiecare citire.

## Sezonul de încălzire

*Sezon de încălzire* decide în ce perioadă se încălzește deloc:

| Mod | Ce face |
| --- | --- |
| **Mereu** (implicit) | Încălzirea e posibilă tot anul. Vara se oprește cu modul *Vară*. |
| **Între date** | Doar între *Început sezon* și *Sfârșit sezon* (implicit 10-15 și 04-15, adică 15 octombrie – 15 aprilie, format luna-ziua). |
| **Automat (temperatura exterioară)** | Sezonul începe după *Sezon automat: zile consecutive* (implicit 3) zile la rând cu media zilnică sub *Prag sezon automat* (implicit 15 °C) și se termină după tot atâtea zile la rând peste prag. |

Pentru modul automat, media fiecărei zile e ponderată în timp și adunată pe
măsură ce vin valorile (o repornire nu o strică). Contează cele X zile dinaintea
zilei de azi, la rând: o zi fără nicio valoare întrerupe șirul.

**Exemplu.** Cu valorile implicite, la 20 octombrie mediile zilnice au fost
16, 14, 13 și 12 °C (17–20 octombrie). Pe 21, ultimele 3 zile (18, 19, 20
octombrie: 14, 13, 12 °C) sunt toate sub 15 °C: sezonul începe.

În afara sezonului camerele nu încălzesc (antiînghețul rămâne activ), iar
învățarea se oprește. Mișcarea robinetelor merge și în afara sezonului.

## Compensarea exterioară

*Compensare exterioară* (oprit implicit) adaugă **Compensare** (implicit
+0,5 °C) la țintă cât temperatura de afară e sub **Compensează sub** (implicit
−5 °C). Când e foarte frig, pereții sunt reci și aceeași temperatură se simte
mai rece.

**Exemplu.** Ținta `home` e 21 °C, afară sunt −8 °C: ținta devine
21 + 0,5 = 21,5 °C.

## Câștigul solar

Setare pe cameră (*Câștig solar*, între −3 și 0 °C, la pasul *Extra*), care
apare doar cu o entitate meteo. Cât e soare, ținta camerei scade cu
valoarea aleasă, pentru camerele care se încălzesc de la soare (de exemplu o
sufragerie cu ferestre mari spre sud).

„Soare” înseamnă: soarele e la cel puțin 10° deasupra orizontului (după
`sun.sun`) și entitatea meteo spune `sunny`, `clear` sau `partlycloudy`.

**Exemplu.** Sufrageria are câștigul solar −1 °C și `home` 21 °C. La prânz,
cu cer senin, ținta e 21 − 1 = 20 °C.

## Ignorarea ferestrelor când e cald

*Ignoră ferestrele peste* (gol implicit): când temperatura de afară e la această
valoare sau peste, o fereastră deschisă nu mai reduce încălzirea. Primăvara și
toamna, o aerisire nu răcește mult camera.

## Cum se adună ajustările

Compensarea, tariful, fotovoltaicul și câștigul solar se adună. Suma e limitată
la ±3 °C și se aplică doar unei ținte de încălzire normale, niciodată unui
antiîngheț (mod Oprit sau Vară, în afara sezonului, fereastră deschisă, zi fără
profil). Rezultatul trece apoi prin limitele de siguranță (antiîngheț și
maxim). Cardul arată în *Detalii* ajustările active.
