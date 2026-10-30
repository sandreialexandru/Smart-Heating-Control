# 5. Prezența și vacanța

*[English](05-presence.md) · [Cuprins](README.ro.md)*

Integrarea vrea să știe dacă e cineva acasă, ca să nu încălzească o casă goală.
Pentru asta folosește locația persoanelor (de obicei din aplicația Home
Assistant de pe telefon), senzori de prezență și, opțional, distanța până acasă.

## Cele trei stări ale casei

| Starea | Când | Ce nivel primesc camerele |
| --- | --- | --- |
| **acasă** (`home`) | cineva e acasă (sau toți, după regulă) | programul |
| **aproape** (`nearby`) | nimeni acasă, dar cineva e într-o zonă apropiată (de exemplu în oraș) | `eco` sau temperatura fixă pentru *aproape* |
| **departe** (`far`) | toată lumea e în afara casei și a zonelor apropiate | `away` |

De ce trei stări: dacă ești la muncă în oraș, te poți întoarce în 30 de minute,
deci casa nu trebuie să se răcească prea mult (`eco`). Dacă ești plecat din oraș,
poate scădea mai mult (`away`).

Dacă nu pui nicio zonă apropiată, există doar *acasă* și *departe*. Dacă nu pui
nicio persoană, casa e mereu *acasă* și decide doar programul.

## Cum se stabilește starea fiecărei persoane

Pentru fiecare persoană:

1. starea `home` → **acasă**;
2. numele unei zone apropiate (de exemplu `București`) → **aproape**;
3. cu *Folosește coordonatele pentru zonele apropiate* (pornit implicit):
   - coordonatele GPS ale persoanei sunt în interiorul unei zone apropiate →
     **aproape** (așa se corectează și o stare `not_home` rămasă în urmă, cu
     telefonul de fapt în oraș);
   - persoana e într-o zonă (de exemplu `Birou`) al cărei centru e în
     interiorul unei zone apropiate → **aproape**;
4. altfel → **departe**.

Stările `unknown` și `unavailable` (telefon descărcat, aplicație oprită) nu
schimbă nimic: se păstrează ultima stare cunoscută. Nu sunt niciodată tratate
ca plecare.

Dacă nu se știe nimic despre nicio persoană (de exemplu imediat după prima
pornire), casa e considerată *acasă*, ca să nu fie frig.

## Regula pentru „acasă”

| Regula | Casa e acasă când | Altfel |
| --- | --- | --- |
| **Cel puțin o persoană e acasă** | oricine e acasă | aproape, dacă cineva e aproape; departe, dacă toți sunt departe |
| **Toți sunt acasă** | toți cei cunoscuți sunt acasă | aproape, dacă cineva e acasă sau aproape; departe, dacă toți sunt departe |

**Exemplu cu *Toți sunt acasă*.** Andrei e acasă, Maria e la muncă în oraș:
casa e *aproape* (`eco`). Când vine și Maria, casa e *acasă* (programul).

## Senzori de prezență și modul oaspeți

- **Senzori de prezență** (mmWave, mișcare, un `input_boolean`): cât e pornit
  oricare dintre ei, casa e *acasă*. Util pentru cine nu are telefon (copii,
  bunici) sau ca siguranță.
- **Modul oaspeți** (comutatorul *Mod oaspeți* al casei): ține casa *acasă*
  indiferent de persoane, de exemplu când vin musafiri și tu pleci. Se oprește
  singur după *Modul oaspeți se oprește după* ore (0 = doar manual).

## Întârzierile

- **Întârziere la plecare** (implicit 10 minute): casa trece spre *aproape* sau
  *departe* doar dacă starea rămâne așa atâtea minute. Un drum scurt la magazin
  nu răcește casa. Întârzierea se numără de când a plecat ultima persoană, deci
  o repornire a Home Assistant nu o ia de la capăt.
- **Întârziere la sosire** (implicit 0): casa trece spre *acasă* (sau de la
  *departe* la *aproape*) după atâtea minute. Lasă 0, ca încălzirea să revină
  imediat; mărește doar dacă GPS-ul raportează uneori greșit „acasă”.

**Exemplu.** Pleci la 08:00. Cu întârzierea implicită de 10 minute, casa trece
pe *departe* la 08:10. Dacă te întorci la 08:05 după cheile uitate, nu se
întâmplă nimic.

## Preîncălzirea pe drum spre casă

Când ești *aproape* sau *departe*, casa poate începe să se încălzească **cât
ești pe drum spre casă**, ca să fie cald când ajungi. Ai nevoie de unul dintre:

- integrarea **Proximity** din Home Assistant, cu senzorul de distanță (și
  opțional cel de direcție);
- un senzor de **timp de deplasare** (Waze Travel Time, Google Travel Time).

Cineva e **pe drum spre casă** (*arriving*) când e mai aproape decât
*Preîncălzește sub distanța* (implicit 10 km) **sau** la mai puțin decât
*Preîncălzește sub timpul* (implicit 20 minute). Cu senzorul de direcție setat,
mai trebuie să se și apropie (direcția `towards`), ca să nu pornească
preîncălzirea când stai la un birou aproape de casă.

Cât timp cineva e pe drum spre casă, regulile de prezență nu se aplică:
camerele urmează programul, ca și cum ai fi deja acasă.

**Exemplu.** Te întorci din alt oraș. La 10 km de casă, Proximity raportează
9,8 km și direcția „towards”: casa trece pe program (de exemplu `home`) și se
încălzește cât parcurgi ultimii kilometri.

## Ocuparea camerei

Separat de prezența casei, o cameră poate avea **senzori de ocupare** (mișcare,
mmWave). Dacă nu detectează pe nimeni *Eco după lipsă de ocupare de* minute
(implicit 30), camera trece pe `eco`, chiar dacă e cineva în altă cameră.

Se aplică doar când programul cere un nivel mai cald decât `eco`: de exemplu
noaptea, cu `sleep` mai rece decât `eco`, camera rămâne pe `sleep`.

**Exemplu.** Biroul are un senzor de mișcare. Lucrezi până la 12:00, apoi pleci
din cameră. La 12:30 biroul trece pe `eco`; când intri din nou, revine imediat
pe program.

## Vacanța

Vacanța pune toate camerele pe `away`. Se poate porni în trei feluri:

1. **Modul *Vacanță*** (selectul *Mod* al casei): vacanță până îl schimbi.
2. **Datele vacanței** (*Început vacanță* și *Sfârșit vacanță*, sau serviciul
   `set_vacation`): vacanța începe și se termină singură.
   - Doar cu data de sfârșit: vacanța începe acum.
   - **Preîncălzire înainte de sfârșitul vacanței** (implicit 4 ore):
     programul revine cu atâtea ore înainte de sfârșit, chiar dacă toată lumea
     e încă departe, ca să fie cald la întoarcere.
3. **Vacanța automată**: *Vacanță automată după departe timp de* (implicit 0 =
   oprită). Când toți sunt departe atâtea ore, vacanța pornește singură.
   - Se termină când cineva ajunge *aproape* sau *acasă*, sau când e **pe drum
     spre casă** (casa se preîncălzește).
   - Dacă după asta toți sunt din nou departe (de exemplu ai trecut doar pe
     lângă casă), revine abia după încă atâtea ore departe.
   - Preîncălzirea dinaintea sfârșitului unei vacanțe planificate are
     prioritate față de vacanța automată.

**Modul oaspeți are prioritate față de orice vacanță** (modul, datele sau cea
automată): cât e pornit, camerele urmează programul ca și cum ar fi cineva acasă,
iar banda din card spune că vacanța e suspendată. Când îl oprești, vacanța
continuă (datele și preîncălzirea rămân cum erau). Modul oaspeți nu se oprește
singur din cauza vacanței: setează *Modul oaspeți se oprește după* dacă vrei asta.

Într-o zi fără profil activ în program, vacanța nu aduce `away` (mai cald), ci
rămâne antiînghețul.

**Exemplu.** Pleci duminică dimineața pentru o săptămână și pui sfârșitul
vacanței sâmbăta următoare la 18:00. Cu preîncălzirea implicită de 4 ore, la
14:00 casa revine pe program, deci la 18:00 e cald.

**Exemplu de vacanță automată.** Pui 24 de ore. Pleci vineri la 17:00 la munte
și nu ai setat nicio vacanță. Sâmbătă la 17:00, după 24 de ore departe, casa
trece singură pe vacanță (`away`). Duminică seara, la 10 km de casă, vacanța
automată se termină și casa se încălzește.

Cardul are câmpurile pentru datele vacanței și butonul de anulare. Senzorul
*Prezență* al casei arată în atribute starea fiecărei persoane (`persons`), dacă
cineva e pe drum spre casă (`arriving`), modul oaspeți (`guest_mode`), dacă e
vacanță (`vacation_active`) sau preîncălzirea dinaintea sfârșitului ei
(`vacation_preheating`), și o schimbare care așteaptă întârzierea (`pending`,
`pending_since`).
