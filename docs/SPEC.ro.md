# Smart Heating Control – specificație

[English](SPEC.md) | **Română**

*Ghidul pas cu pas pentru fiecare setare: [guide/README.ro.md](guide/README.ro.md).*

Smart Heating Control calculează **o țintă pentru fiecare cameră** din program,
prezență, ferestre, vreme și modificări manuale, și o aplică dispozitivelor de
încălzire. Totul se configurează din interfață (config flow, options flow și
subintrările camerelor); nu e nevoie de YAML.

Integrarea este construită în jurul **Generic Thermostat (GT)**: folosește
aceleași nume de preseturi și nu schimbă niciodată felul în care funcționează
GT – doar alege presetul potrivit. Sunt acceptate și camere încălzite de alte
termostate, TRV-uri sau relee simple.

## Principii

- **O decizie pentru fiecare cameră, recalculată continuu.** Orice schimbare
  relevantă (persoană, zonă, fereastră, oră, vreme) declanșează o reevaluare,
  nu doar începutul unui interval. O verificare periodică (implicit la 5
  minute) prinde orice a scăpat.
- **O ierarhie a regulilor fixă și explicită** (secțiunea 12), ca două reguli
  să nu se contrazică niciodată.
- **Fiecare decizie are un motiv vizibil**: senzorul *Decizie* al camerei
  arată regula câștigătoare și un text care o explică.
- **Starea se păstrează la repornire**: modificările manuale, vacanța,
  încălzirea și răcirea învățate.
- **Valori implicite sigure**: fără configurare suplimentară integrarea nu
  poate nici lăsa casa să înghețe, nici s-o supraîncălzească.
- **Opțiunile avansate sunt opționale** și rămân oprite până sunt activate.

## 1. Ce se controlează

Unitatea este **camera** (zona de încălzire). Configurarea are două niveluri: o
intrare pentru **casă** (persoane, zone, modul global, setări comune) și o
**subintrare de cameră** pentru fiecare cameră (dispozitive, senzori, ferestre,
program).

| Opțiune | Implicit | Descriere |
| --- | --- | --- |
| Unitatea de temperatură | unitatea Home Assistant | °C sau °F pentru fiecare casă, aleasă prima la configurare și schimbată cu *Reconfigurează* (valorile sunt convertite). Intern totul se păstrează în °C; fiecare dispozitiv e citit și comandat în unitatea lui, așa că unitatea casei poate fi diferită de cea a Home Assistant |
| Încălzit de | Generic Thermostat | Generic Thermostat, alte entități `climate` (TRV-uri, termostate) sau relee `switch` / `input_boolean` |
| Comanda (alte termostate) | temperatură | Temperatură / preset / pornit-oprit prin `hvac_mode` |
| Forțarea TRV | oprită | Doar cu comanda temperatură. Cererea de căldură vine de la senzorii camerei (obligatorii), cu histerezisul; cât durează, TRV-urile primesc temperatura de forțare (gol = maximul casei; niciodată sub țintă, niciodată peste maximul casei sau al TRV-urilor), altfel ținta. Se aplică la orice cerere de căldură, inclusiv antiînghețul; nu la mișcarea robinetelor sau la dispozitivele oprite. O pauză aduce o forțare rămasă pe TRV-uri înapoi la țintă o dată |
| Senzori externi de temperatură | niciunul | Folosiți în locul senzorului dispozitivului; mai mulți senzori → medie, minim sau mediană |
| Calibrare TRV | oprită | Offset calculat din senzorul extern sau temperatura externă scrisă în intrarea TRV-ului (în unitatea entității TRV) |
| Toleranța termostatului | GT: cold tolerance; relee: histerezis; altele: 0 | Cât lasă termostatul camera să coboare sub țintă înainte să încălzească; episoadele de încălzire se învață de la atât sub țintă |
| Cererea de căldură | `hvac_action` | Termostatele fără `hvac_action` sunt tratate ca releele: se consideră că încălzesc de la histerezis sub temperatura setată până la histerezis peste ea, iar oprirea anticipată folosește histerezisul ca toleranță; histerezisul se cere când un termostat nu raportează `hvac_action` sau e indisponibil la configurare |
| Sursa de căldură | niciuna | Centrala (sau releul care pornește sursa de căldură) când camerele nu o pot porni singure (TRV-uri, robinete de zonă); pornită când destule camere cer căldură (cu timpi minimi de pornire / oprire). O sursă de tip `climate` merge cât `hvac_action` e heating, când îl raportează |
| Încălzire | sursa de căldură pornită | O cameră încălzește (învățare, timp de încălzire) doar cât merge sursa ei: GT încălzește, releul sau termostatul on / off e pornit și, când e setată, și *Sursa de căldură*; cu TRV-uri și fără sursă, cererea TRV-ului. Cât timp starea sursei e necunoscută nu se folosește niciun episod. Cu TRV-uri și o centrală pornită de un termostat din afara Home Assistant învățarea nu e sigură |
| Camere necesare | 1 | Câte camere trebuie să ceară căldură ca să pornească sursa de căldură. Are prioritate față de pornirea anticipată: cu mai mult de 1, o cameră aflată în pornire anticipată așteaptă până cer căldură destule camere, deci poate ajunge la țintă mai târziu |
| Cameră de referință | niciuna | Doar această cameră decide pentru sursa de căldură |
| Alertă diferență între camere | oprită | Alertă când o cameră rămâne sub țintă în timp ce altele sunt calde |

## 2. Niveluri (preseturi)

Integrarea folosește **numele de preseturi ale Generic Thermostat**, fiecare cu
un rol fix în reguli:

| Preset | Se aplică automat când |
| --- | --- |
| `home` | Cineva e acasă și programul spune `home` |
| `sleep` | Intervalul de somn din program, cu cineva acasă |
| `eco` | Nimeni acasă, cel puțin o persoană în zona apropiată |
| `away` | Toată lumea în afara zonelor apropiate, sau vacanță |
| `comfort`, `activity` | Fără rol automat în reguli |
| `min_temp` al GT (nu e preset) | Antiîngheț: fereastră deschisă, mod Oprit |

Toate preseturile GT rămân disponibile ca preseturi: pot fi alese manual sau
folosite în program. Integrarea doar alege presetul; nu schimbă nicio funcție a
GT.

Pentru *aproape* implicit este presetul `eco`. În locul presetului se poate
configura o **temperatură fixă**; integrarea o trimite la GT, care trece singur
pe presetul `none`. Cu *Nu peste program* (pe cameră, nebifat implicit) se aplică
cea mai mică dintre nivelul / temperatura pentru aproape și program, ca în oraș
noaptea să nu se încălzească mai mult decât acasă.

Fără Generic Thermostat rolurile din reguli rămân aceleași, iar setările camerei
depind de comandă:

| Comandă | Nivelurile în setările camerei |
| --- | --- |
| Preset | Fiecare nivel alege unul dintre **preseturile termostatului** (citite de pe dispozitiv). Termostatul păstrează acea temperatură; integrarea o învață pentru afișare. Un nivel fără preset e atins trimițând temperatura lui. |
| Temperatură | **Nume** configurabile și o **temperatură** pentru fiecare nivel; temperatura e trimisă dispozitivului. |
| Pornit / oprit (`hvac_mode`) | **Nume** configurabile și o **temperatură** pentru fiecare nivel; preseturile dispozitivului nu se folosesc, integrarea îl pornește și îl oprește în jurul temperaturii nivelului. |

Temperaturile din setările camerei se pot schimba și mai târziu din card sau din
entitățile număr (câte una pentru fiecare nivel controlat de integrare). Se
setează între antiînghețul și temperatura maximă ale casei.

## 3. Program

Programul spune ce nivel se dorește cât timp cineva e acasă. Prezența și
celelalte reguli îl pot coborî, dar niciodată ridica.

```
workday: 00:00 sleep, 06:00 home, 22:00 sleep
weekend: 00:00 sleep, 08:00 home, 23:00 sleep
fri:     00:00 sleep, 06:00 home, 23:30 sleep
home_office: 00:00 sleep, 07:00 comfort, 23:00 sleep
```

| Opțiune | Implicit | Descriere |
| --- | --- | --- |
| Profiluri | workday + weekend | Orice nume; fiecare cu zilele lui (toate, zile lucrătoare, weekend și sărbători sau zile anume) și pornit / oprit, setate din card. Profilurile active nu se suprapun (zilele anume doar între ele) |
| Alegerea profilului | auto | Eveniment de calendar → profilul activ al zilei → profilul activ al zilelor lucrătoare / weekendului → profilul activ pentru toate zilele → niciunul: protecție la îngheț, cu alertă |
| Zile lucrătoare | integrarea Workday | Sărbătorile vin din integrarea Workday (inclusiv zilele viitoare) |
| Calendar | niciunul | Un eveniment cu numele unui profil alege acel profil pentru toată ziua din program din care acoperă o parte (azi și următoarele 7 zile la fel; citit de la începutul zilei de azi, în fiecare oră și când calendarul se schimbă); numele unui preset alege acel nivel cât durează evenimentul |
| Sursa programului | intern | Program intern sau un **Schedule helper** existent în HA |
| Pornire anticipată | oprită | Începe încălzirea mai devreme, ca nivelul următor să fie atins la timp |
| Încălzirea învățată | activă cu pornirea anticipată | Minute pe cameră = parte fixă + grade × (minute pe grad la 0 °C + schimbarea pe grad de afară × temperatura de afară), calculate prin metoda celor mai mici pătrate din ultimele 25 de episoade mici (< 1 °C) și 25 mari (≥ 1 °C), fiecare cu gradele, minutele și temperatura medie de afară. Partea fixă cere episoade care diferă ca mărime cu cel puțin 1 °C, termenul de afară episoade la temperaturi de afară care diferă cu cel puțin 1 °C; termenii imposibili (parte fixă sau minute negative) se pun pe zero și restul se recalculează; temperaturile de afară neîntâlnite prelungesc linia (anticiparea maximă o limitează în continuare). Un episod începe de la cel puțin toleranța termostatului sub țintă și se folosește când cererea de căldură a durat cel puțin 10 minute și temperatura a crescut, oricât de puțin; episoadele cu un senzor de fereastră deschis nu se folosesc. Până la primul episod 60 de minute pe grad. Învățarea salvată înainte de 2.0 (o viteză pe episod) se renunță. Încălzirea și răcirea se învață doar în sezonul rece (nu în modurile Oprit sau Vară și nici în afara sezonului) |
| Pornire anticipată maximă | 2 h (10 min – 24 h) | Limita pornirii anticipate. Odată începută, pornirea anticipată continuă până la schimbare (celelalte reguli o pot suprascrie) |
| Răcirea învățată | activă cu oprirea anticipată | Un coeficient pe cameră al diferenței interior / exterior (media ultimelor 30 de episoade). Un episod durează de la sfârșitul până la începutul cererii de căldură și se folosește când a durat cel puțin 10 minute și temperatura a scăzut, oricât de puțin; episoadele cu un senzor de fereastră deschis nu se folosesc |
| Toleranța opririi anticipate | GT: cold tolerance; relee, forțarea TRV și termostate fără `hvac_action`: histerezis; altele: 0 | Confortul păstrat de oprirea anticipată: cât poate coborî camera sub nivelul curent înainte de schimbare |
| Oprire anticipată maximă | 30 min (5 min – 24 h) | Limita opririi anticipate; până se învață răcirea, nivelul mai mic începe cu atât mai devreme |
| Temperatura de afară pentru pornirea / oprirea anticipată | automat | Cu prognoză orară a entității meteo: media ponderată în timp a prognozei din perioada în care rulează pornirea / oprirea (fiecare valoare e valabilă pentru ora ei, valoarea măsurată până la următoarea oră din prognoză), recalculată de 3 ori pornind de la perioada găsită înainte; fără o prognoză care acoperă perioada: temperatura de afară de acum. Prognoza se citește la fiecare 30 de minute când o folosește pragul după prognoză sau o cameră cu pornire / oprire anticipată |
| Oprire anticipată | oprită | Are nevoie de o temperatură de afară (senzor sau meteo; fără ea valorile de afară salvate se șterg). Coboară nivelul cât de devreme se poate răci camera rămânând în confortul nivelului curent (toleranța de mai sus); răcirea se învață din perioadele fără cerere de căldură, ca un coeficient al diferenței interior / exterior; limitată de un maxim; continuă odată începută și se anulează (nivelul curent până la schimbare) dacă camera coboară sub confort |
| Începutul zilei | 00:00 | Pentru ture de noapte: când se schimbă ziua programului |

## 4. Prezență

Prezența casei are trei stări: **acasă / aproape / departe**, plus ocuparea
opțională a fiecărei camere.

| Opțiune | Implicit | Descriere |
| --- | --- | --- |
| Persoane | – | Ce entități `person` contează |
| Regula pentru acasă | cel puțin una | „Cel puțin una” sau „toată lumea” acasă |
| Zone apropiate | niciuna | Zone (de exemplu București) în care casa e *aproape* în loc de *departe* |
| Zone din interiorul unei zone apropiate | automat | O zonă din oraș (de exemplu Birou) contează și ea ca aproape, calculat după coordonate |
| Proximity | oprit | Distanță și direcție; preîncălzire doar când cineva vine spre casă |
| Prag de sosire | 10 km sau 20 min | Distanța sau timpul de drum de la care începe preîncălzirea |
| Întârziere la plecare | 10 min | Așteptare înainte ca o casă să fie considerată goală |
| Întârziere la sosire | 0 min | Așteptare înainte ca cineva să fie considerat sosit |
| Senzori de prezență | niciunul | mmWave / mișcare / comutatoare țin casa *acasă* |
| Ocuparea camerei | oprită | Camera trece pe eco după X minute fără ocupare |
| Mod oaspeți | oprit | Forțează *acasă*, cu expirare automată opțională |

Stările `unknown` / `unavailable` ale persoanelor sunt tratate ca „nicio
schimbare”, niciodată ca plecare.

## 5. Ferestre și uși

O fereastră deschisă coboară camera la antiîngheț sau oprește încălzirea; când
se închide, camera revine la ce spun regulile în acel moment.

| Opțiune | Implicit | Descriere |
| --- | --- | --- |
| Senzori de fereastră | niciunul | Oricare deschis = deschis |
| Întârziere la deschidere | 60 s | Ignoră aerisirile foarte scurte |
| Întârziere la închidere | 30 s | Așteptare înainte de reluare |
| Acțiune | antiîngheț | Antiîngheț sau oprit |
| Detectare după temperatură | oprită | O scădere rapidă (de exemplu 1 °C în 3 min) contează ca fereastră deschisă; un salt pentru că un senzor de temperatură s-a oprit sau a revenit (ori a preluat senzorul dispozitivului) nu e o scădere: detectarea pornește din nou de la valoarea nouă |
| Ferestrele altor camere | niciuna | de exemplu ușa de balcon a sufrageriei afectează și holul |
| Alertă după | 30 min | Notificare cât timp încălzirea contează |
| Ignoră peste temperatura de afară | oprit | Primăvara / toamna aerisirea nu coboară încălzirea |

## 6. Vreme și sezon

Vremea poate opri încălzirea sau ajusta ținta; nu o poate ridica niciodată peste
ce cere programul.

| Opțiune | Implicit | Descriere |
| --- | --- | --- |
| Temperatura de afară | `weather` | Senzor local sau entitatea meteo. Oprirea când e cald, sezonul automat, compensarea și ignorarea ferestrelor au nevoie de una (altfel formularul de opțiuni le refuză; salvate fără: alertă, iar sezonul automat contează ca mereu pornit); nicio temperatură de la nicio sursă configurată (senzorul, altfel temperatura din meteo) mai mult de timpul de alertă: alertă |
| Prag de oprire | 18 °C | Încălzire oprită când media e la prag sau peste; repornește la prag − histerezis sau sub (histerezis 1 °C) |
| Medie pe | 6 h (cel puțin 1 h) | Media, nu valoarea instantanee. Este și cât rămâne valabilă o valoare de afară: fără o valoare nouă în acest timp, temperatura de afară e necunoscută (fără prag de oprire, compensare sau ferestre ignorate, fără episoade de învățare, fără oprire anticipată) până când senzorul sau meteo raportează din nou |
| Sezon de încălzire | mereu | Mereu, între date (de exemplu 10-15 → 04-15) sau automat |
| Sezon automat | 3 zile / 15 °C | Începe / se termină după X zile consecutive sub / peste prag (cele X zile dinaintea zilei de azi; fiecare zi cu media ponderată în timp a timpului acoperit, adunată pe măsură ce vin valorile și salvată, deci un restart nu o schimbă; o zi fără nicio valoare întrerupe șirul) |
| Compensare după temperatura de afară | oprită | Ajustare mică, de exemplu +0,5 °C sub −5 °C |
| Prognoză | oprită | Are nevoie de o entitate meteo și de oprirea când e cald. Doar media prognozei pe următoarele ore de prognoză (fiecare valoare pentru ora ei, valoarea măsurată până la următoarea oră din prognoză), niciodată o singură oră. Încălzire oprită de media măsurată și acea medie la temperatura de repornire sau sub ea: încălzirea poate porni (camerele încălzesc la nevoie); peste ea: încălzirea rămâne oprită. Încălzire pornită și acea medie la prag sau peste: încălzirea se oprește mai devreme și rămâne oprită până când media scade la temperatura de repornire (același histerezis ca la media măsurată; starea se salvează) |
| Câștig solar pe cameră | oprit | Ajustare negativă cât e soare (are nevoie de entitatea meteo) |

## 7. Modificări manuale

O schimbare făcută de o persoană (aplicație, TRV, HA) este respectată un timp
definit; apoi integrarea preia din nou controlul.

| Opțiune | Implicit | Descriere |
| --- | --- | --- |
| Detectare | activă | Schimbările făcute de integrare se recunosc după context, sau pentru că dispozitivul doar raportează valorile trimise de integrare (și valorile trimise în ultimele 5 minute și valoarea arătată înainte de fiecare comandă, până când dispozitivul arată ultima valoare de 2 minute: o valoare veche raportată târziu, sau încă o dată după cea nouă, e recunoscută și ea) |
| Durată | configurabilă, universală | O singură regulă pentru orice modificare manuală, inclusiv oprirea GT: **durată fixă** (X ore) sau **până la următoarea reevaluare** declanșată de o schimbare (interval, prezență, fereastră, mod). Verificarea periodică nu o încheie |
| Domeniu | cameră | Toată casa doar când camerele au robinete proprii |
| Pauză | – | Comutator: nicio comandă, fără calibrarea TRV (antiînghețul și temperatura maximă se aplică în continuare) |
| Blocare pentru copii | oprită | Modificările manuale sunt anulate imediat |
| Anulare | – | Buton pentru fiecare cameră și pentru casă |
| Card / serviciu | – | Un nivel sau o temperatură puse din card sau cu `set_override` se trimit doar cât se aplică modificarea manuală (nu în pauză, cu fereastra deschisă, în modul Oprit / Vară…) și rămân pe dispozitive tot timpul ei |
| După o întrerupere | – | Când o regulă de mai sus a schimbat dispozitivele în timpul unei modificări manuale (fereastră, antiîngheț, mod), valoarea manuală se pune din nou după ce se termină: valoarea din card / serviciu sau ce a pus persoana pe dispozitiv (mod, preset, temperatură, releu pornit / oprit). Temperatura maximă o limitează definitiv |

## 8. Moduri globale

Un select pentru casă: **Auto / Vacanță / Oprit / Vară**.

| Mod | Ce face | Opțiuni |
| --- | --- | --- |
| Auto | Program + prezență + toate regulile | – |
| Vacanță | `away` în toate camerele | Date de început și sfârșit (doar sfârșit: de acum), preîncălzire cu X ore înainte de sfârșit (implicit 4 h; programul se aplică chiar dacă toată lumea e departe), vacanță automată după Y ore departe (preîncălzirea dinaintea sfârșitului unei vacanțe planificate are prioritate; se termină când cineva e pe drum spre casă și revine doar după alte Y ore departe) |
| Oprit | Doar antiîngheț (`min_temp` al GT) | – |
| Vară | Încălzire oprită | Comutare automată cu sezonul (secțiunea 6) |

## 9. Energie și protecția sursei de căldură

| Opțiune | Implicit | Descriere |
| --- | --- | --- |
| Histerezis | 0,3 °C | Relee, control pornit / oprit și termostate fără `hvac_action` (nu cu GT, care are propriile toleranțe) |
| Timp minim de pornire / oprire | 5 / 5 min | Doar relee (nu cu GT); se numără de la ultima comutare, și una făcută de mână; camera e evaluată din nou când se termină (la fel pentru sursa de căldură a casei); în banda de histerezis releul își păstrează starea reală; o valoare manuală refăcută după o fereastră îl așteaptă și ea |
| Tarif dinamic | oprit | Coboară cu X °C peste un preț, preîncălzește sub un preț |
| Surplus fotovoltaic | oprit | Ridică cu X °C când există surplus |
| Statistici | active | Ore de încălzire pe cameră și pentru casă |

## 10. Siguranță și reziliență

| Opțiune | Implicit | Descriere |
| --- | --- | --- |
| Antiîngheț | activ | Limita de jos, și în modurile Oprit și Pauză (GT: temperatura lui minimă); odată ce încălzește, continuă până când dispozitivul nu mai cere căldură. O cameră în antiîngheț pornește singură sursa de căldură (fără camere necesare, fără camera de referință, și în pauză). Camerele cu TRV-uri și senzori proprii: se decide după senzorul camerei (sub antiîngheț până la el + histerezis), iar TRV-urile primesc între timp maximul casei (sau temperatura de forțare) |
| Temperatură maximă | 25 °C | Limita de sus a oricărei ținte: un nivel peste ea se trimite ca maxim, o temperatură setată peste ea (modificare manuală, pauză) e coborâtă la ea, o cameră cu releu sau comandată cu hvac_mode e oprită cât temperatura camerei e la maxim sau peste (modificare manuală, pauză; nu e pornită din nou ca să încălzească la loc), serviciul și cardul rămân în limită, iar un termostat care rotunjește la pasul lui primește pasul imediat sub maxim. Apare ca regula *Temperatură maximă* |
| Senzor indisponibil | senzorul dispozitivului | Senzor extern căzut → senzorul dispozitivului → eco (niciodată peste program: un nivel mai jos, de exemplu away, rămâne), cu alertă |
| Dispozitiv indisponibil | alertă după 15 min | Celelalte camere funcționează în continuare; și pentru sursa de căldură (atunci nici antiînghețul nu poate încălzi) |
| Verificarea comenzilor | activă | Reîncearcă o dată după 2 min, apoi alertă |
| Mișcarea robinetelor | oprită | Deschidere completă săptămânală a TRV-urilor, în orice mod (și vara și în afara sezonului); o pauză, o modificare manuală sau o fereastră deschisă o amână pentru mai târziu în aceeași zi; nu cere căldură și perioada ei nu se învață |
| Baterie descărcată | alertă sub 20 % | TRV-urile și senzorii camerei |
| Repornire | restaurare | Modificările manuale, vacanța și datele învățate se păstrează; și episodul de încălzire în curs (continuă dacă după repornire camera încă încălzește, altfel se renunță la el) |
| Reevaluare periodică | 5 min | Pe lângă evenimente |
| Valori invalide | refuzate | O valoare de senzor, un atribut sau o valoare salvată care nu e număr (`nan`, `inf`) e tratată ca indisponibilă sau e eliminată; un senzor de temperatură fără unitate e citit în unitatea casei. `set_override` refuză o temperatură care nu e număr și o durată în afara intervalului 0,25–72 h (ca în formular); entitățile vacanței refuză un sfârșit care nu e după început; un profil `set_schedule` greșit dă o eroare clară |
| Un singur proprietar pe dispozitiv | verificare în formular | Un termostat sau un releu e comandat de o singură cameră (din toate casele); sursa de căldură nu e dispozitivul unei camere; releul unui Generic Thermostat folosit de o cameră nu e nici dispozitiv de cameră, nici sursă de căldură; senzorul exterior nu e senzor de temperatură al unei camere. Senzorii pot fi comuni |
| Camere necesare | ≤ camere | Formularul permite cel mult numărul de camere ale casei; alertă când se șterg camere și rămân mai puține |
| Timp | UTC intern | Duratele (timp de încălzire, învățare, modificări manuale, întârzieri, preîncălzirea dinaintea sfârșitului vacanței) sunt în timp real, și peste schimbarea orei; programul, zilele lucrătoare și mediile zilnice folosesc ora locală. Un interval din program aflat în ora repetată la sfârșitul orei de vară se aplică o singură dată (la prima apariție); unul din ora sărită primăvara începe când se termină acea oră (de exemplu 03:30 → 04:00). |

## 11. Vizibilitate

| Entitate / interfață | Arată |
| --- | --- |
| `sensor.<room>_decision` | Regula câștigătoare (enum) + motiv, preset, program, următoarea schimbare, planul, timpul până la țintă, temperatura estimată la schimbare în timpul unei opriri anticipate, dacă o oprire anticipată a fost anulată, următoarea pornire / oprire anticipată (`next_estimate`: tip, schimbare, preset, trimis ca preset sau temperatură, temperatura nivelului, minute, început, temperatura de afară și sursa ei, învățat) |
| `sensor.<room>_target_temperature`, `sensor.<room>_room_temperature` | Ținta și temperatura camerei, în unitatea casei |
| `sensor.<room>_heating_rate` | Minutele pe grad învățate pentru temperatura de afară de acum (parte fixă, estimări, episoade) |
| `sensor.<room>_cooling_rate` | Cât de repede scade camera acum fără încălzire (coeficient, episoade, toleranță) |
| `sensor.<room>_heating_runtime`, `sensor.<house>_heating_runtime` | Timpul total de încălzire (total crescător): o cameră cât merge sursa ei, casa cât merge sursa de căldură (fără ea, cât încălzește o cameră) |
| `sensor.<room>_next_change` | Următoarea schimbare din program |
| `binary_sensor.<room>_heat_demand` | Dacă camera cere căldură; atributul `heating` arată dacă sursa ei merge |
| `sensor.<house>_presence` | acasă / aproape / departe |
| `select.<house>_mode` | Modul global |
| `number.*`, `button.*`, `switch.*` | Niveluri, anularea modificărilor manuale, resetarea învățării încălzirii / răcirii (pe cameră), mod oaspeți, pauză, blocare pentru copii |
| Servicii | `set_override`, `clear_override`, `set_vacation`, `reevaluate`, `set_schedule` |
| Evenimente | `advanced_climate_decision_changed` cu camera, ținta veche și nouă și motivul |
| Cardul Lovelace | Starea și decizia camerei; grafic pe 24 h (temperatură, țintă, încălzire) cu următoarele 12 h planificate și zoom până la minut (o bară sub graficul mărit îl mută; tragerea pe grafic citește valorile); program editabil prin tragere (5 minute), copierea unei zile; timpul până la țintă sau, în timpul unei opriri anticipate, temperatura estimată la schimbare; următoarea pornire / oprire anticipată în detaliile camerei; grafic cu grilă pe grade, ținta ca linie în trepte, încălzirea pe o bandă separată, temperatura de afară (măsurată și prognozată) pe banda ei și următoarea pornire / oprire anticipată; de ce nu încălzește o cameră sub țintă; de ce e oprită încălzirea pentru că e cald (media măsurată sau media prognozei) sau că prognoza o lasă să pornească; bandă de pauză; starea învățării și alertele în detalii; originea modificării manuale; linkuri către entități; timpul de încălzire pe zi / săptămână / lună; mod compact (o placă pe cameră); temperatura camerei ca arc între antiîngheț și maxim (doar afișare); profilul zilei ca bară; butoane care deschid separat secțiunile camerei; butoanele casei (Pauză și Oaspeți comută direct, cu o bandă sus cât sunt pornite; Vacanță își deschide datele); camera deschisă arată decizia lângă nume și nivelul separat; camera pliată doar nivelul și iconițe de stare (încălzire, fereastră, modificare manuală, mod oaspeți) |
| Diagnostic | Configurația și ultimele 100 de decizii |

## 12. Ierarhia regulilor

Regulile sunt evaluate de sus în jos pentru fiecare cameră; prima regulă care se
aplică stabilește nivelul.

1. **Siguranță** – antiîngheț și temperatură maximă, aplicate mereu: și unei
   modificări manuale, în pauză, serviciului `set_override` și cardului, iar
   antiînghețul pornește singur sursa de căldură
2. **Pauză**
3. **Mișcarea robinetelor** – în orice mod, nu cu o fereastră deschisă
4. **Mod Oprit / Vară / în afara sezonului**
5. **Fereastră deschisă**
6. **Modificare manuală**
7. **Vacanță** (o zi fără profil activ: antiîngheț, peste `away`)
8. **Prezență** – departe → `away` (o zi fără profil activ: antiîngheț), aproape → `eco` (sau temperatura fixă; cu *Nu peste program* cea mai mică dintre ea și program), acasă → program
9. **Program** – cu pornire / oprire anticipată și ocuparea camerei

Ajustările finale (prag de temperatură exterioară, compensare, tarif,
fotovoltaic, câștig solar) corectează o țintă de încălzire doar cu câteva zecimi
de grad (niciodată un antiîngheț: modul Oprit sau Vară, în afara sezonului,
fereastră, zi fără profil), iar rezultatul trece mereu prin limitele de
siguranță. Motivul arătat
de senzorul de decizie este regula câștigătoare.

## 13. Glosar RO → EN

| Română | English |
| --- | --- |
| Casă / cameră | house / room |
| Program / profil / interval | schedule / profile / time slot |
| Prezență: acasă / aproape / departe | presence: home / nearby / far |
| Zonă apropiată | nearby zone |
| Fereastră deschisă | window open |
| Intervenție manuală | manual override |
| Durată fixă / până la următoarea reevaluare | fixed duration / until next reevaluation |
| Mod global: Auto / Vacanță / Oprit / Vară | global mode: auto / vacation / off / summer |
| Pauză | pause |
| Antiîngheț | frost protection |
| Pornire / oprire anticipată | optimal start / optimal stop |
| Sezon de încălzire | heating season |
| Prag de oprire (temperatură exterioară) | outdoor cutoff |
| Câștig solar | solar gain |
| Viteză de încălzire / răcire | heating rate / cooling rate |
| Toleranța termostatului | thermostat tolerance |
| Toleranța opririi anticipate | optimal stop tolerance |
| Unitatea de temperatură | temperature unit |
| Sursa de căldură | heat source |
| Cererea către centrală | heat demand |
| Mod oaspeți | guest mode |
| Motiv curent | decision reason |
| Mișcarea robinetelor | valve exercise |
| Reevaluare | reevaluation |
