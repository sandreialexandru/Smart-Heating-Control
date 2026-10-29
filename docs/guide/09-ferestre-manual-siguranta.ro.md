# 9. Ferestre, modificări manuale și siguranță

*[English](09-windows-manual-safety.md) · [Cuprins](README.ro.md)*

## Ferestre și uși

Când se deschide o fereastră, nu are rost să încălzești afara. Integrarea
reacționează pe cameră.

**Ce se întâmplă:**

1. Fereastra se deschide. Dacă rămâne deschisă *Întârziere la deschidere*
   (implicit 60 de secunde), camera trece pe *Când o fereastră e deschisă*:
   - **Antiîngheț** (implicit): camera păstrează temperatura minimă;
   - **Oprire**: încălzirea se oprește (la dispozitivele care nu se pot opri, se
     trimite antiînghețul).
2. Fereastra se închide. După *Întârziere la închidere* (implicit 30 de
   secunde), camera revine la ce spun regulile în acel moment (program,
   prezență, o modificare manuală care era activă).

Aerisirile mai scurte decât întârzierea la deschidere sunt ignorate.

**Mai multe surse pentru „fereastră deschisă”:**

- **Senzori de fereastră** ai camerei: oricare deschis = deschis;
- **Ferestre din alte camere**: de exemplu ușa de balcon din sufragerie răcește
  și holul;
- **Detectarea din temperatură**: o scădere de *Scădere de temperatură*
  (implicit 1 °C) în *În* (implicit 3 minute) e tratată ca fereastră deschisă
  15 minute. Pentru camere fără senzori. Un salt al temperaturii camerei pentru
  că un senzor de temperatură s-a oprit sau a revenit, ori pentru că camera a
  trecut pe senzorul dispozitivului, nu e o scădere: detectarea pornește din nou
  de la valoarea nouă.

**Când e cald afară**: cu *Ignoră ferestrele peste* (opțiunile casei), o
fereastră deschisă nu reduce încălzirea când temperatura de afară e la acea
valoare sau peste.

**Alertă**: dacă o fereastră rămâne deschisă mai mult de *Alertă când o
fereastră e deschisă mai mult de* (implicit 30 de minute) cât timp încălzirea e
necesară, primești o alertă.

Episoadele de învățare în care o fereastră a fost deschisă nu se folosesc.

## Modificările manuale

O **modificare manuală** e orice schimbare făcută de o persoană: pe termostat,
pe TRV, în aplicație, în Home Assistant, din card sau cu serviciul
`set_override`. Integrarea o respectă un timp, apoi preia din nou controlul.

**Cum le recunoaște.** Comenzile trimise de integrare au un „context” propriu în
Home Assistant, deci integrarea știe care sunt ale ei. Un dispozitiv care doar
raportează mai târziu ce i-a trimis integrarea (de exemplu un TRV Zigbee pe
baterie care se trezește rar) nu e o modificare manuală.

**Cât durează** (*Modificările manuale se păstrează*, în opțiunile casei):

| Alegere | Se termină |
| --- | --- |
| **Durată fixă** (implicit, 2 ore) | după *Durată fixă* ore |
| **Până la următoarea reevaluare** | când se schimbă ceva important: nivelul din program, profilul, prezența, cineva e pe drum spre casă, vacanța sau preîncălzirea ei, o fereastră, modul, oprirea când e cald, sezonul. Verificarea periodică nu o termină. |

**Exemplu cu *Până la următoarea reevaluare*.** E 20:00, programul cere `home`
21 °C până la 22:00, iar tu pui 23 °C pe termostat. Schimbarea ține până la
22:00, când programul trece pe `sleep`; atunci camera trece pe `sleep`.

**Pe ce se aplică** (*Modificarea manuală se aplică*): **Doar acea cameră**
(implicit) sau **Toată casa** (o schimbare într-o cameră e copiată în toate;
doar când fiecare cameră are robinete proprii).

**Dacă o regulă mai importantă intervine.** Dacă în timpul unei modificări
manuale se deschide o fereastră (sau intervine antiînghețul, sau se schimbă
modul), dispozitivele se schimbă după acea regulă. Când regula se termină,
valoarea manuală e pusă din nou: valoarea din card / serviciu, sau ce ai pus tu
pe dispozitiv (mod, preset, temperatură, releu pornit / oprit). La un releu,
refacerea respectă timpul minim pornit / oprit. Cardul arată *revine după: …*
cât timp e întreruptă.

**Din card sau din serviciu.** Un nivel sau o temperatură puse din card (*Setează
temporar*) sau cu `set_override` se trimit doar cât se aplică modificarea
manuală (nu în pauză, nu cu fereastra deschisă, nu în modul Oprit sau Vară) și
rămân pe dispozitive tot timpul ei. Cât o regulă de mai sus o ține departe,
cardul arată *se aplică după: …*. Temperatura e mereu între antiîngheț și maxim.

**Anularea**: butonul *Anulează modificarea manuală* al camerei, *Înapoi la automat* în
card, butonul casei pentru toate camerele, sau serviciul `clear_override`.

## Blocarea pentru copii

Comutatorul *Blocare modificări* al camerei (și în card, la *Setează temporar*): orice
modificare manuală pe dispozitiv e anulată imediat, iar camera revine la decizia
integrării. Util pentru un TRV la îndemâna copiilor.

## Pauza

Comutatorul *Pauză* al casei oprește toate comenzile integrării: nu se schimbă
nimic pe dispozitive și nu se face calibrarea TRV. Rămân active, pentru
siguranță:

- **antiînghețul**: o cameră prea rece primește căldură (și sursa de căldură e
  pornită pentru ea, apoi oprită);
- **temperatura maximă**: o temperatură setată peste maxim e coborâtă, iar o
  cameră cu releu sau comandată pornit / oprit e oprită cât e la maxim sau
  peste;
- **forțarea TRV**: o forțare rămasă pe TRV-uri când începe pauza e adusă
  înapoi la țintă o dată (vezi [capitolul 3](03-camere.ro.md)).

În card apare o bandă sus cât timp casa e în pauză. O modificare manuală făcută
în pauză se păstrează și se aplică după pauză: una din card sau din serviciu se
trimite atunci, una făcută pe dispozitiv rămâne cum e (blocarea pentru copii nu
o anulează în pauză).

## Modurile casei

Selectul *Mod* al casei:

| Mod | Ce face |
| --- | --- |
| **Auto** | Toate regulile: program, prezență, ferestre, vreme… |
| **Vacanță** | `away` în toate camerele (vezi [capitolul 5](05-prezenta.ro.md#vacanța)) |
| **Oprit** | Doar antiîngheț |
| **Vară** | Încălzire oprită (antiînghețul rămâne ca siguranță). Cu sezonul automat sau între date, încălzirea se oprește singură în afara sezonului. |

## Antiînghețul

Cea mai mică temperatură pe care o primește vreodată o cameră:

- valoarea *Antiîngheț* din opțiunile casei (implicit 7 °C, între 3 și 15 °C);
- la camerele cu Generic Thermostat, temperatura minimă a GT (`min_temp`).

Se aplică **mereu**: în modul Oprit, în pauză, peste o modificare manuală, cu
fereastra deschisă. Odată ce o cameră încălzește pentru antiîngheț, continuă
până când dispozitivul nu mai cere căldură (nu pornește și oprește în jurul
limitei). Un nivel setat sub antiîngheț (de exemplu în Generic Thermostat) e
ridicat la antiîngheț, iar decizia arată *Antiîngheț (sleep e sub 7°)*.

Niciun nivel nu poate fi setat în integrare sub antiîngheț: câmpurile, cardul
și serviciile au antiînghețul ca minim.

**TRV-uri cu senzor în cameră.** Un TRV măsoară lângă calorifer, mai cald decât
în cameră: cu camera la 5 °C și TRV-ul citind 8 °C (valori de exemplu), un TRV
setat la 7 °C nu s-ar deschide. De aceea, într-o cameră cu TRV-uri și senzori
de temperatură proprii, antiînghețul se decide după senzorul camerei: sub
antiîngheț camera cere căldură (pornește sursa de căldură), iar TRV-urile
primesc temperatura maximă a casei (sau temperatura de forțare a camerei, cu
forțarea TRV), până când camera ajunge la antiîngheț + histerezis. Apoi primesc
iar temperatura de antiîngheț. Histerezisul e setarea camerei; când pașii de
dinainte nu l-au cerut, pasul *Senzori: detalii* îl cere ca *Histerezis la
antiîngheț*.

## Temperatura maximă

*Temperatură maximă* (implicit 25 °C, între 15 și 35 °C). Nicio țintă nu trece
de ea:

- un nivel mai mare e trimis ca maxim;
- o temperatură setată pe termostat peste maxim (modificare manuală, pauză) e
  coborâtă la maxim;
- o cameră cu releu sau comandată pornit / oprit e **oprită** cât temperatura
  camerei e la maxim sau peste; sub maxim nu e pornită din nou ca să încălzească
  la loc;
- un termostat care rotunjește la pasul lui primește pasul imediat sub maxim.

Decizia arată atunci regula *Temperatură maximă*.

## Senzori defecți

Dacă senzorii de temperatură ai camerei sunt indisponibili:

1. se folosește senzorul dispozitivului (termostat, TRV), dacă are;
2. dacă nici acela nu merge, camera trece pe `eco`, dar niciodată peste program:
   dacă programul cere un nivel mai jos (de exemplu `away`), rămâne acela.

În ambele cazuri primești o alertă. O valoare a senzorului care nu e număr
(`nan`, `inf`) e tratată ca indisponibilă.

## Verificarea comenzilor

Cu *Verifică comenzile* (pornit implicit), la 2 minute după o comandă integrarea
verifică dacă dispozitivul a acceptat-o (și pentru o modificare manuală din
card). Dacă nu, o retrimite o dată; dacă nici atunci, dă alerta *… nu a acceptat
…*. Oprește verificarea doar dacă un dispozitiv își raportează starea foarte
încet.

## Mișcarea robinetelor

Pentru TRV-uri (*Mișcarea robinetelor*, la pasul *Extra* al camerei): o dată pe
săptămână, în ziua și la ora alese (implicit duminică la 10:00), TRV-urile se
deschid complet 5 minute, contra depunerilor de calcar. Se face în orice mod,
și vara și în afara sezonului. O pauză, o modificare manuală sau o fereastră
deschisă o amână mai târziu în aceeași zi. Nu cere căldură de la centrală, iar
perioada ei nu se învață.

## Alertele

Alertele apar ca notificări în Home Assistant sau prin *Serviciu de notificare*
și, în limba cardului, în *Detaliile* camerei. O alertă se repetă cel mult la
câteva ore.

| Alertă | Când |
| --- | --- |
| O fereastră e deschisă de peste … min | fereastra deschisă mai mult de pragul de alertă, cât e nevoie de căldură |
| … e indisponibil de peste … min | un termostat sau senzor indisponibil mai mult de pragul de alertă |
| Sursa de căldură … e indisponibilă | atunci nu se încălzește deloc, nici pentru antiîngheț |
| Nicio temperatură de afară de la … | nicio sursă configurată (senzor, meteo) nu dă temperatura mai mult de pragul de alertă |
| Pornite, dar nu funcționează fără senzor de temperatură exterioară sau entitate meteo | funcții de vreme pornite fără sursa de care au nevoie |
| Senzorii de temperatură sunt indisponibili | se folosește senzorul dispozitivului sau `eco` |
| Baterie descărcată la … | sub *Baterie descărcată sub* (implicit 20 %) |
| … nu a acceptat … | verificarea comenzilor a eșuat de două ori |
| Unele camere rămân reci, altele sunt calde | cu *Alertă când o cameră rămâne mai rece cu* |
| Nivelul … nu există pe … | un preset ales pentru un nivel lipsește de pe termostat și temperatura lui e necunoscută |
| Programul e invalid | se folosește programul implicit |
| Fără profil activ în program: … | zile fără profil activ (antiîngheț) |
| Camere necesare pentru pornirea sursei de căldură: … | mai multe camere necesare decât are casa (au fost șterse camere): sursa pornește doar pentru antiîngheț |

## Repornirea Home Assistant

Se păstrează: modificările manuale, vacanța și vacanța automată, modul, pauza,
oaspeții, învățarea încălzirii și a răcirii (și episodul de încălzire în curs),
mediile de afară (inclusiv
mediile zilnice pentru sezon), oprirea după prognoză, timpii ultimelor comutări
ale centralei și releelor și dacă centrala a fost pornită pentru antiîngheț.
După repornire, integrarea continuă de unde a rămas.
