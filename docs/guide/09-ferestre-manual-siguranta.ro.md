# 9. Ferestre, modificări manuale și siguranță

*[English](09-windows-manual-safety.md) · [Cuprins](README.ro.md)*

## Ferestre și uși

Când se deschide o fereastră, nu are rost să se încălzească afara. Integrarea
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
  trecut pe senzorul dispozitivului ori unul dintre TRV-uri s-a oprit, nu e o scădere: detectarea pornește din nou
  de la valoarea nouă.

**Când e cald afară**: cu *Ignoră ferestrele peste* (opțiunile casei), o
fereastră deschisă nu reduce încălzirea când temperatura de afară e la acea
valoare sau peste.

**Alertă**: dacă o fereastră rămâne deschisă mai mult de *Alertă când o
fereastră e deschisă mai mult de* (implicit 30 de minute) cât timp încălzirea e
necesară, apare o alertă.

Cât timp un senzor de fereastră sau ușă e deschis, nu se învață nimic.

## Modificările manuale

O **modificare manuală** e orice schimbare făcută de o persoană: pe termostat,
pe TRV, în aplicație, în Home Assistant, din card sau cu serviciul
`set_override`. Integrarea o respectă un timp, apoi preia din nou controlul.

**Cum le recunoaște.** Comenzile trimise de integrare au un „context” propriu în
Home Assistant, deci integrarea știe care sunt ale ei. Un dispozitiv care doar
raportează mai târziu ce i-a trimis integrarea (de exemplu un TRV Zigbee pe
baterie care se trezește rar) nu e o modificare manuală, nici când raportează o
valoare mai veche după ce a fost trimisă una nouă: se recunosc și valorile
trimise în ultimele 5 minute și temperatura sau presetul pe care le arăta
dispozitivul înainte de fiecare comandă, până când dispozitivul arată ultima valoare de 1 minut (unele
TRV-uri arată imediat valoarea nouă, apoi mai raportează o dată pe cea veche);
după aceea orice altă valoare e o modificare manuală.

**Limitele dispozitivului.** Unele TRV-uri au pe dispozitiv propriile *Max
temperature* / *Min temperature*, mai înguste decât intervalul entității (de
exemplu 25 °C pe un TRV Tuya a cărui entitate merge până la 35 °C). Când un TRV
raportează mai puțin decât a trimis temperatura cât încălzește sau mișcarea robinetelor (dar cel
puțin ținta), sau mai mult decât a trimis antiînghețul / oprirea (dar sub cel mai
jos nivel), aceea e limita lui, nu o modificare manuală: comenzile următoare
rămân în ea, iar o alertă o spune. O limită se învață doar în 5 minute de la
comandă și doar cât TRV-ul nu a arătat valoarea trimisă: odată ce a arătat-o, a
acceptat-o, deci o altă valoare după aceea e a unei persoane (modificare
manuală). Un TRV care își ținea deja limita (deci
nu raportează nimic) e recunoscut de verificarea comenzilor: după ce comanda a
fost retrimisă și TRV-ul tot o ține. Limita se încearcă din nou după o zi,
ca o setare nouă pe dispozitiv să fie văzută.

**Cât durează** (*Modificările manuale se păstrează*, în opțiunile casei):

| Alegere | Se termină |
| --- | --- |
| **Durată fixă** (implicit, 2 ore) | după *Durată fixă* ore |
| **Până la următoarea reevaluare** | când se schimbă ceva important: nivelul din program, profilul, prezența, cineva e pe drum spre casă, vacanța sau preîncălzirea ei, o fereastră, modul, oprirea când e cald, sezonul. Verificarea periodică nu o termină. |

**Exemplu cu *Până la următoarea reevaluare*.** E 20:00, programul cere `home`
21 °C până la 22:00, iar cineva pune 23 °C pe termostat. Schimbarea ține până la
22:00, când programul trece pe `sleep`; atunci camera trece pe `sleep`.

**Pe ce se aplică** (*Modificarea manuală se aplică*): **Doar acea cameră**
(implicit) sau **Toată casa** (o schimbare într-o cameră e copiată în toate;
doar când fiecare cameră are robinete proprii).

**Dacă o regulă mai importantă intervine.** Dacă în timpul unei modificări
manuale se deschide o fereastră (sau intervine antiînghețul, sau se schimbă
modul), dispozitivele se schimbă după acea regulă. Când regula se termină,
valoarea manuală e pusă din nou: valoarea din card / serviciu, sau ce s-a pus
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
- **încălzirea după senzorul camerei**: o temperatură mai mare rămasă pe TRV-uri
  când începe pauza e adusă înapoi la țintă o dată ([capitolul 3](03-camere.ro.md)).

În card apare o bandă sus cât timp casa e în pauză. O modificare manuală făcută
în pauză se păstrează și se aplică după pauză: una din card sau din serviciu se
trimite atunci, una făcută pe dispozitiv rămâne cum e (blocarea pentru copii nu
o anulează în pauză).

## Modurile casei

Selectul *Mod* al casei:

| Mod | Ce face |
| --- | --- |
| **Auto** | Toate regulile: program, prezență, ferestre, vreme… |
| **Plecat** | Nu e nimeni acasă, setat de mână: `away` în toate camerele, până se schimbă (vezi [capitolul 5](05-prezenta.ro.md#modul-plecat)) |
| **Vacanță** | `away` în toate camerele ([capitolul 5](05-prezenta.ro.md#vacanța)) |
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
primesc temperatura maximă a casei (sau temperatura cât încălzește a camerei, cu
*Încălzește după senzorul camerei*), până când camera ajunge la antiîngheț + histerezis. Apoi primesc
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

În ambele cazuri apare o alertă. O valoare a senzorului care nu e număr
(`nan`, `inf`) e tratată ca indisponibilă.

## Verificarea comenzilor

Cu *Verifică comenzile* (pornit implicit), la 2 minute după o comandă integrarea
verifică dacă dispozitivul a acceptat-o (și pentru o modificare manuală din
card). Dacă nu, o retrimite o dată; dacă nici atunci, dă alerta *… nu a acceptat
…*. Verificarea se oprește doar dacă un dispozitiv își raportează starea foarte
încet.

## Mișcarea robinetelor

Pentru TRV-uri (*Mișcarea robinetelor*, la pasul *Extra* al camerei): o dată pe
săptămână, în ziua și la ora alese (implicit duminică la 10:00), TRV-urile se
deschid complet 5 minute, contra depunerilor de calcar. Se face în orice mod,
și vara și în afara sezonului. O pauză, o modificare manuală sau o fereastră
deschisă o amână mai târziu în aceeași zi. Nu cere căldură de la centrală, iar
perioada ei nu se învață.

## Alertele

Alertele apar în card, în *Detaliile* camerei, în limba cardului. Se și
trimit, în limba Home Assistant (română sau engleză), destinatarilor aleși în
opțiuni (*Alerte*), după cât de importante sunt:

- **importante**: fără încălzire, sursa de căldură sau un termostat
  indisponibil. Se trimit imediat, și în orele de liniște;
- **avertizări**: toate celelalte alerte din lista de mai jos. În orele de
  liniște așteaptă sfârșitul lor și se trimit doar dacă mai sunt valabile;
- **informații**: ce a făcut casa singură: a început sau s-a încheiat sezonul
  de încălzire, a început o vacanță planificată, casa se încălzește înainte de
  întoarcere, a pornit sau s-a încheiat vacanța automată, modul oaspeți s-a
  oprit singur. Nu apar în card.

Un destinatar e un serviciu de notificare (un telefon, `notify.mobile_app_...`)
sau o entitate de notificare. Pentru email se scriu adresele după serviciu:
`notify.eu_gmail_com: ana@exemplu.ro, ion@exemplu.ro`. Integrarea Google Mail nu
trimite nimic fără ele; cu SMTP configurat în YAML, fără adrese scrise se
folosesc cele din configurarea lui.

O categorie fără destinatari devine notificare în Home Assistant (informațiile
atunci nu se anunță). Cu *Anunță când o alertă se încheie* se anunță și un
dispozitiv care funcționează din nou, o fereastră închisă, o baterie schimbată
sau o comandă acceptată din nou; pe telefon (`notify.mobile_app_...`) mesajul
înlocuiește alerta. O alertă se repetă cel mult la câteva ore.

O casă configurată înainte de 2.5 cu un *Serviciu de notificare* trimite în
continuare toate alertele acolo până când opțiunile *Alerte* sunt salvate din
nou: formularul îl propune atunci ca destinatar pentru alertele importante și
pentru avertizări.

| Alertă | Când |
| --- | --- |
| O fereastră e deschisă de peste … min | fereastra deschisă mai mult de pragul de alertă, cât e nevoie de căldură |
| … e indisponibil de peste … min | un termostat sau senzor indisponibil mai mult de pragul de alertă (importantă) |
| Sursa de căldură … e indisponibilă | atunci nu se încălzește deloc, nici pentru antiîngheț (importantă) |
| Nicio temperatură de afară de la … | nicio sursă configurată (senzor, meteo) nu dă temperatura mai mult de pragul de alertă |
| Pornite, dar nu funcționează fără senzor de temperatură exterioară sau entitate meteo | funcții de vreme pornite fără sursa de care au nevoie |
| Senzorii de temperatură sunt indisponibili | se folosește senzorul dispozitivului sau `eco` |
| … nu a mai trimis temperatura de peste … h | un senzor de temperatură al camerei rămâne disponibil, dar nu a trimis nicio valoare (nici aceeași) cât *Alertă când un senzor de temperatură nu trimite nimic* (implicit 12 h), cât încălzirea e pornită (nu oprită, vară sau pauză); se încheie când senzorul trimite din nou |
| Încălzește de … h, dar temperatura a crescut doar cu …° | vezi *Încălzire fără efect* mai jos |
| Baterie descărcată la … | sub *Baterie descărcată sub* (implicit 20 %) |
| … nu a acceptat … | verificarea comenzilor a eșuat de două ori |
| … acceptă cel mult / cel puțin … | TRV-ul ține propria limită *Max / Min temperature* de pe dispozitiv (mai sus, *Limitele dispozitivului*) |
| Unele camere rămân reci, altele sunt calde | cu *Alertă când o cameră rămâne mai rece cu* |
| Nivelul … nu există pe … | un preset ales pentru un nivel lipsește de pe termostat și temperatura lui e necunoscută |
| Programul e invalid | se folosește programul implicit |
| Fără profil activ în program: … | zile fără profil activ (antiîngheț) |
| Camere necesare pentru pornirea sursei de căldură: … | mai multe camere necesare decât are casa (au fost șterse camere): sursa pornește doar pentru antiîngheț |
| Camera are …°, sub temperatura de antiîngheț | camera e cu 0,5° sau mai mult sub ea: încălzirea nu o poate menține (se anunță și când revine) |
| Încălzirea e în pauză de peste … h | pauza e pornită mai mult de *Amintește când pauza durează mai mult de* (implicit 12 h), apoi o dată pe zi |
| Risc de mucegai: umiditatea la peretele cel mai rece a ajuns la circa …% | doar pentru o cameră cu *Senzor de umiditate* și o casă cu temperatură de afară: vezi *Riscul de mucegai* mai jos |

### Riscul de mucegai

Aerul camerei își păstrează vaporii de apă; locul cel mai rece al unui perete
exterior (un colț, marginea unei ferestre) e mai rece decât aerul, deci aceiași
vapori înseamnă acolo o umiditate mai mare. Mucegaiul poate crește unde acea
umiditate rămâne la **80 %** sau mai mult (criteriul standardului DIN 4108-2).

Alerta are nevoie de un **Senzor de umiditate** în cameră (pasul *Senzori* al
camerei) și de o **temperatură de afară** a casei (senzor sau entitate meteo).
Fără oricare dintre ele nu se trimite nicio alertă de mucegai.

1. Peretele cel mai rece: afară + 0,70 × (cameră − afară). 0,70 e minimul cerut
   de standard unui perete la o punte termică; o casă mai veche poate fi mai
   rece. Când e mai cald afară decât înăuntru, niciun perete nu e mai rece
   decât camera, deci se folosește temperatura camerei: umiditatea la pereți e
   atunci cea a camerei.
2. Umiditatea acolo: vaporii din aerul camerei (umiditatea ei × presiunea de
   saturație la temperatura camerei) împărțiți la presiunea de saturație la
   temperatura peretelui (formula Magnus).
3. Alerta se trimite când a rămas la 80 % sau mai mult **60 de minute** (ca un
   duș sau gătitul să nu o declanșeze) și se încheie sub **75 %**. Cât timp
   senzorul de umiditate sau temperatura de afară e indisponibil, o alertă deja
   trimisă rămâne: nu se știe dacă riscul a trecut.

**Exemplu**: camera la 20 °C cu 60 % umiditate, afară 0 °C. Peretele: 0 + 0,70 ×
20 = 14 °C. Presiunea de saturație: 23,3 hPa la 20 °C, 16,0 hPa la 14 °C;
vaporii 0,60 × 23,3 = 14,0 hPa înseamnă 14,0 ÷ 16,0 = **88 %** la perete: alerta
se trimite după o oră. Cu 50 % în cameră: circa 73 %, nicio alertă. Senzorul
*Decizie* arată valoarea în `surface_humidity`.

Ce ajută: aerisirea scurtă și des, rufele uscate în altă parte, camera nu prea
rece, mobila la câțiva centimetri de pereții exteriori.

### Încălzire fără efect

O cameră e urmărită cât încălzește fără oprire, cu cel puțin 0,5° sub țintă (un
TRV care ține ținta raportează încălzire în continuu, și e în regulă), fără
fereastră deschisă, în afara antiînghețului și a pauzei. După *Alertă când
încălzirea nu are efect* (implicit 2 h), creșterea ei e comparată cu creșterea
pe care o așteaptă modelul învățat de la același început, la aceeași
temperatură de afară. Alerta se trimite sub o treime din ea. O cameră cu
încălzirea prea slabă pentru frigul de afară așteaptă puțin (sub 0,3°) și nu
primește alertă: nu are nimic stricat. **Înainte ca o cameră să-și învețe
modelul nu există alertă**: o încălzire lentă, de exemplu în pardoseală, poate
crește foarte puțin în primele ore și nu s-ar deosebi de una blocată.

Cauzele obișnuite: un ventil blocat,
o sursă de căldură care nu pornește, o fereastră deschisă fără senzor, un
calorifer plin de aer. Alerta se încheie când camera se încălzește (0,3° peste
temperatura de la alertă, sau aproape de țintă). Un TRV care raportează că nu
încălzește (măsoară un loc cald al lui) nu contează ca încălzire, deci nu e
semnalat aici: un senzor extern cu calibrare ([capitolul 3](03-camere.ro.md))
rezolvă asta.

**Exemplu**: o cameră învățată la 18 °C, care ar trebui să crească cu
aproximativ 1,4° în 2 ore, a crescut cu 0,2°: se trimite alerta. Dacă ar fi
crescut cu 0,8°, nu.

## Repornirea Home Assistant

Se păstrează: modificările manuale, vacanța și vacanța automată, modul, pauza,
oaspeții, învățarea fiecărei camere (nu și cele 30 de minute în curs de măsurare),
mediile de afară (inclusiv
mediile zilnice pentru sezon), oprirea după prognoză, timpii ultimelor comutări
ale centralei și releelor și dacă centrala a fost pornită pentru antiîngheț.
După repornire, integrarea continuă de unde a rămas.

Nu se păstrează (la repornire sau la reîncărcarea integrării): limitele
învățate din ce aplică TRV-urile pe dispozitiv (propriile Max / Min
temperature). Se învață din nou la prima forțare sau comandă care le atinge,
deci o repornire sau o reîncărcare e și felul de a le uita înainte să treacă
ziua.
