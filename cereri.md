# Cereri și idei

Principiu: SHC automatizează încălzirea (ce temperatură, când, și pornirea sursei comune); nu încălzește el, nu reglează aparatele în locul lor și nu alege cu ce energie se încălzește.

Stare: **de decis** · **mai târziu** · **există deja** · **nu facem** · **făcut** · **rezolvat**

## De la utilizatori

| Cerere | De unde | Stare | Note |
|---|---|---|---|
| Moduri proprii pentru toată casa (ex. „Work - Home” / „Work - Office”), fără prezență pe telefon | GitHub #9 | făcut | 2.6.4: modul *Away* al casei (setat de mână), selectul *Schedule profile* pe fiecare cameră (arată profilul ales, atributul `today` pe cel de azi) și **scenariile** (profile pentru mai multe camere, alese din casă). Exista deja și calendarul: eveniment cu numele unui profil = acel profil toată ziua; cu numele unui nivel = nivelul cât ține evenimentul. |
| Mai multe zone (sus / jos) cu o centrală și ventile de zonă | GitHub | există deja | Fiecare zonă = o „cameră” cu releul ventilului și senzorii etajului (Minimum / Average), centrala ca sursă a casei. Două case nu: aceeași centrală nu poate fi sursă în două case. |
| TRV dintr-o cameră care deschide ventilul zonei lui (circuite: pardoseală / calorifere, fiecare cu pompa lui) | GitHub #10 (și cererea cu zonele) | făcut | 2.6.5rc3: *Circuit relays* la casă și *Circuit* la cameră; releul pornește înaintea centralei și se oprește după ea; centrala nu pornește pentru o cameră cu circuitul oprit. |
| A doua sursă electrică pe cameră (pompă aer-aer, AC) folosită când curentul e ieftin, TRV-ul ca rezervă | GitHub | nu facem | În afara principiului. Alte integrări aleg sursa (TRV principal, AC secundar, după diferență și temperatura de afară), fără tarif. Soluție: două camere cu același senzor (TRV la ținta normală, pompa cu +0,5–1 °C, fără sursa casei), oprită / pornită prin `set_override` / `clear_override` după senzorul lui de „curent ieftin”. |
| Cerere de căldură în procente / centrale cu modulare (Ariston Sensys) | Discord / Facebook | rezolvat | Verificat 2026-11-12: acoperit (senzorii binari *Heat demand* ai casei și camerelor; Sensys ca sursă a casei). |
| Pauză când pompa de căldură face apă caldă (Ecodan DHW) | Discord (callumt) | rezolvat | `switch.home_pause` pornit dintr-o automatizare când pompa face apă caldă. |
| Listă „Tested with” (dispozitive testate) în README | noi | făcut | Din issue-urile #1, #2, #5, #6, #10; tado (#8) și termostatele Tuya Wi-Fi (#1) lăsate deoparte până la confirmare. |
| Camere secundare: nu pornesc centrala, primesc căldură doar când o pornește altă cameră | noi | făcut | 2.6.5rc1: bifa *Can start the house heat source* (implicit pornit), doar la camerele sursei casei; antiînghețul pornește totuși centrala; nu se numără la Camere necesare; nu oprește camera ținută deschisă. |
| Ține deschis TRV-ul ultimei camere până cere căldură alta (căldura rămasă a centralei, baterie, zgomot noaptea) | Reddit r/homeassistant (ex-utilizator tado) | făcut | 2.6.4rc8: bifa *Keep the last TRV open* la sursa casei, fără limită (cine o bifează acceptă depășirea țintei); TRV-urile primesc maximul camerei (Pornit/oprit: pornit; Preset: temperatura); camera nu cere căldură; învățarea sare peste acel timp; se termină când cere altă cameră, o regulă mai puternică sau camera are nevoie de căldură. |

## Idei

| Idee | Stare | Note |
|---|---|---|
| Alertă pentru senzor înghețat (aceeași valoare mult timp) | făcut | 2.6.4: *senzor tăcut*, după `last_reported` (nu a trimis nimic, nici aceeași valoare), implicit 12 h. O temperatură constantă nu e tăcere. Senzorii template / de grup scriu doar la o schimbare: limita se mărește pentru ei. |
| Alertă „încălzește mult fără să crească temperatura” | făcut | 2.6.4: *încălzire fără efect*, implicit 2 h, sub o treime din creșterea așteptată de model. Doar cu modelul învățat (o pardoseală lentă nu se deosebește de un ventil blocat). După ce camera se încălzește, urmărirea începe din nou. |
| „Coop start”: o cameră încălzește doar când sursa merge deja | există deja | *Rooms needed to start the heat source*: sursa pornește doar când cer căldură atâtea camere; o cameră singură primește căldură doar când sursa merge pentru altele. |
| Ține „pe drum spre casă” 15–20 min, ca să nu sară | rezolvat | Verificat 2026-11-12: acoperit (schimbarea prezenței are deja întârziere). |
| Perechi Proximity pe persoană | de decis | Timpul de drum ia deja câte un senzor pe persoană (2.6.4, contează cel mai scurt); Proximity are deja *nearest* pentru cea mai apropiată persoană. |
| Direcția din tendința timpului de drum (Waze / Maps) | de decis | |
| Card: −/+ la temperatură, mai puține butoane de secțiuni, rândul „ce urmează”, aranjare pe tabletă | rezolvat | Cardul nou (2.6.4); senzorul *Next change* și rândul „ce urmează” în card. |
| Început de zi: între 00:00 și primul interval, motorul ia ultimul interval al zilei de dinainte, cardul arată ultimul interval al aceleiași zile | rezolvat | Motorul și cardul fac la fel: ultimul interval ține până la primul din ziua următoare. |
| Învățare după o schimbare voită (curba centralei, calorifere): reset doar al puterii încălzirii, păstrând pierderea | rezolvat | Resetări separate: `reset_heating_learning` (doar puterea încălzirii) și `reset_cooling_learning`. |
| Selectul de profil sau un scenariu care lasă zile fără profil (ex. `home_office` pe zile lucrătoare oprește un profil pe toate zilele, weekendul rămâne gol) | există deja | Alerta „Fără profil activ” o spune, ca în card. Decis 2026-11-09: nu se schimbă. |

## Din alte integrări (verificat 2026-11-12)

Versatile Thermostat, Better Thermostat, RoomMind, Advanced Heating Control (blueprint), ZEAL, Vesta: funcțiile lor și cererile cu cele mai multe reacții de pe GitHub.

| Idee | De unde | Stare | Note |
|---|---|---|---|
| O entitate `climate` pe cameră (ținta, nivelul, pornit/oprit), pentru asistenții vocali, cardurile de termostat, HomeKit / Google / Alexa | RoomMind („Unified climate entity per room”), ZEAL | de decis | SHC nu are `climate` pe cameră. Ținta schimbată de acolo = modificare manuală; presetul = nivelul; off = camera oprită. |
| Încălzire „la ocazie”: cât centrala merge deja, camerele aproape de țintă se încălzesc și ele, ca centrala să pornească mai rar | Versatile Thermostat (12 reacții) | de decis | Generalizează camerele secundare: o cameră sub țintă cu cel mult X °C își deschide TRV-ul doar cât merge centrala pentru altă cameră. |
| Comutator „controlată de SHC” pe cameră (o cameră lăsată temporar în pace, din automatizări) | Better Thermostat (cererea deschisă cu cele mai multe reacții), RoomMind | de decis | |
| Estimarea economiei (ore de încălzire evitate, kWh / cost) | Vesta, statisticile RoomMind | de decis | SHC are deja timpul de funcționare pe casă și pe cameră; o estimare ar fi aproximativă. |
| Reglarea directă a deschiderii ventilului (%) | Versatile Thermostat | nu facem | Reglează aparatul în locul lui: în afara principiului. |
| Prezență din entități care nu sunt `person` (input_boolean, alarmă) | RoomMind | există deja | Modul *Away* al casei se poate seta dintr-o automatizare; în camere, senzorii de ocupare. |
