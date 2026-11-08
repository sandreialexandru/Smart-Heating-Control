# Cereri și idei

Ce cer utilizatorii și ce ne-a venit nouă, cu ce am decis. Se completează pe
parcurs.

Stare: **de decis** · **mai târziu** · **există deja** · **nu facem** · **făcut**

## De la utilizatori

| Cerere | De unde | Stare | Note |
|---|---|---|---|
| Moduri proprii pentru toată casa (ex. „Work - Home” / „Work - Office”), fără prezență pe telefon | GitHub #9 | există deja | Calendarul: eveniment cu numele unui profil = acel profil toată ziua în toate camerele care îl au; eveniment cu numele unui nivel (ex. `away` 9–17) = nivelul cât ține evenimentul. Răspuns dat, cu recomandarea să citească ghidul. |
| Mai multe zone (sus / jos) cu o centrală și ventile de zonă | GitHub | există deja | Fiecare zonă = o „cameră” cu releul ventilului și senzorii etajului (Minimum / Average), centrala ca sursă a casei. Două case nu: aceeași centrală nu poate fi sursă în două case. |
| TRV dintr-o cameră care deschide ventilul zonei lui | GitHub (aceeași cerere cu zonele) | de decis | Nu există. Întrebat dacă are TRV-uri pe camere. |
| A doua sursă electrică pe cameră (pompă aer-aer, AC) folosită când curentul e ieftin, TRV-ul ca rezervă | GitHub | nu facem | SHC decide ce temperatură și când, nu cu ce energie. Soluție: două camere cu același senzor (TRV la ținta normală, pompa cu +0,5–1 °C, fără sursa casei), oprită / pornită prin `set_override` / `clear_override` după senzorul lui de „curent ieftin”. |
| Cerere de căldură în procente / centrale cu modulare (Ariston Sensys) | Discord / Facebook | de decis | Acum: senzorul binar „Heat demand” al casei și al camerelor; Sensys poate fi sursa casei fără boost (doar heat / off). Idee: senzor de cerere în procente. |
| Pauză când pompa de căldură face apă caldă (Ecodan DHW) | Discord (callumt) | mai târziu | Rezolvat acum cu `switch.home_pause` dintr-o automatizare. Idee: o intrare „sursa e ocupată”. |
| Listă „Tested with” (dispozitive testate) în README | noi | mai târziu | |

## Idei de-ale noastre

| Idee | Stare | Note |
|---|---|---|
| Alertă pentru senzor înghețat (aceeași valoare mult timp) | de decis | Din PiHome. Siguranță, utilă oricui. |
| Alertă „încălzește mult fără să crească temperatura” | de decis | Din PiHome. Siguranță. |
| „Coop start”: o cameră încălzește doar când sursa merge deja | de decis | Din PiHome. Economie, pentru case cu TRV-uri. |
| Ține „pe drum spre casă” 15–20 min, ca să nu sară | de decis | |
| Perechi Proximity pe persoană | de decis | |
| Direcția din tendința timpului de drum (Waze / Maps) | de decis | |
| Card: −/+ la temperatură, mai puține butoane de secțiuni, rândul „ce urmează”, aranjare pe tabletă | de decis | |
| Început de zi: între 00:00 și primul interval, motorul ia ultimul interval al zilei de dinainte, cardul arată ultimul interval al aceleiași zile | mai târziu | Găsit 2026-11-08. Ocolire: interval la 00:00 în fiecare profil. Variantă de reparat: motorul ca în card. |
| Învățare după o schimbare voită (curba centralei, calorifere): reset doar al puterii încălzirii, păstrând pierderea | de decis | Simulat 2026-11-07: resetul complet reînvață în ~1,5 zile; 5 zile de înjumătățire ajută puțin. Cel puțin o propoziție în ghid. |
