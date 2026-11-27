# Cereri și idei

Principiu: SHC automatizează încălzirea (ce temperatură, când, și pornirea sursei comune); nu încălzește el, nu reglează aparatele în locul lor și nu alege cu ce energie se încălzește.

Stare: **de decis** · **mai târziu** · **există deja** · **nu facem** (ce e făcut sau rezolvat se scoate de aici; e în CHANGELOG)

## De la utilizatori

| Cerere | De unde | Stare | Note |
|---|---|---|---|
| Mai multe zone (sus / jos) cu o centrală și ventile de zonă | GitHub | există deja | Fiecare zonă = o „cameră” cu releul ventilului și senzorii etajului (Minimum / Average), centrala ca sursă a casei. Două case nu: aceeași centrală nu poate fi sursă în două case. |
| A doua sursă electrică pe cameră (pompă aer-aer, AC) folosită când curentul e ieftin, TRV-ul ca rezervă | GitHub | nu facem | În afara principiului. Soluție: două camere cu același senzor (TRV la ținta normală, pompa cu +0,5–1 °C, fără sursa casei), oprită / pornită prin `set_override` / `clear_override` după senzorul lui de „curent ieftin”. |
| Verificări de sănătate: TRV pe programul lui intern, valvă deschisă permanent (preset `on`), TRV cu corecție proprie de temperatură, contact de fereastră care raportează foarte des, cameră care nu se încălzește niciodată, calorifer care abia ține pasul, TRV cu multe comenzi pe zi + zile rămase de baterie | noi | de decis | Avem deja: senzor mut (`sensor_silent`), fereastră deschisă mult (`window_long`), baterie, aparat/sursă/circuit indisponibil, comenzi neacceptate (`not_accepted`), fără efect (`no_effect`), diferență între camere (`room_difference`). |
| Entitate `climate` pe cameră + dashboard | noi | mai târziu | Împreună, într-un release spre Crăciun. |
| Eurotronic Spirit / Comet (SPZB0001, COZB0001, CoZB_dha): *heat* = boost (ventil deschis la maxim, Z2M setează flag-ul boost); cu comanda Temperatură SHC trece TRV-ul de pe *auto* pe *heat* (din 2.6.4) | noi (verificare baza Z2M, 2026-11-15) | mai târziu | **Risc asumat deocamdată.** Variante discutate: opțiune în cameră „Lasă termostatul pe auto” (implicit oprită, universală) sau detectare automată (pe *heat* doar dacă TRV-ul își schimbă singur ținta pe *auto*). Fără listă de modele hardcodată. |
| TRV-uri cu pas de 0,5° și țintă cu zecimale (ex. 20,8° din offset-uri de preț / PV / compensare de câte 0,1°, sau casă în °F): TRV-ul ține 21, SHC retrimite 20,8 (13 comenzi în 30 min, și cu senzor extern) | noi (verificare baza Z2M, 2026-11-15) | mai târziu | **Risc asumat; vedem dacă se plânge cineva.** Reglajul camerei nu e afectat (decide senzorul camerei), doar bateria TRV-ului și traficul Zigbee. Fără `target_temp_step` raportat, rotunjirea poate fi luată drept modificare manuală. Reparația propusă: rotunjire la pasul TRV-ului înainte de trimitere și „ținută” la mai puțin de un pas. |

## Idei

| Idee | Stare | Note |
|---|---|---|
| „Coop start”: o cameră încălzește doar când sursa merge deja | există deja | *Rooms needed to start the heat source*: sursa pornește doar când cer căldură atâtea camere; o cameră singură primește căldură doar când sursa merge pentru altele. |
| Perechi Proximity pe persoană | de decis | Timpul de drum ia deja câte un senzor pe persoană (2.6.4, contează cel mai scurt); Proximity are deja *nearest* pentru cea mai apropiată persoană. |
| Direcția din tendința timpului de drum (Waze / Maps) | de decis | |
| Panou propriu „Încălzire” în bara laterală (pagină întreagă, nu card) | de decis | Discutat 2026-11-12, mock-up în artifactul *SHC heating panel*. Ecran lat: în stânga casa (mod, scenariu, acțiuni temporare, grupate cu linii subțiri) și lista camerelor; în dreapta camera aleasă: arcul cu Acum / Urmează / Învățat, graficul pe toată lățimea (24 h / 3 / 7 zile), jos programul, nivelurile, detaliile. Telefon: plăcile camerelor, pagina camerei cu file (Acum, Grafic, Program, Niveluri, Detalii). Refolosește bucățile cardului (`_houseHtml`, `_roomHtml`, `_timelineHtml`, `_quickHtml`, `_levelsHtml`, `_detailsHtml`, `_alertsHtml`, `_scheduleHtml`, `_learnHtml`); bifă în opțiuni pentru cine nu îl vrea. Estimare: ~1.000–1.500 linii JS plus teste; în două etape (ecran lat, apoi telefon, cu riscul butonului înapoi din aplicația mobilă). |
| Dashboard generat automat (dashboard strategy): casa sus, câte un card pe cameră în grilă, opțional o pagină pe cameră | de decis | Alternativa mai mică la panou: același card, așezat automat; utilizatorul poate prelua controlul și îl modifică. Până atunci: un exemplu în ghid cu mai multe carduri (`show_rooms: false` pentru casă, `show_house: false` + `rooms:` pe cameră). |
| Selectul de profil sau un scenariu care lasă zile fără profil (ex. `home_office` pe zile lucrătoare oprește un profil pe toate zilele, weekendul rămâne gol) | există deja | Alerta „Fără profil activ” o spune, ca în card. Decis 2026-11-09: nu se schimbă. |

## Alte idei (2026-11-12)

| Idee | De unde | Stare | Note |
|---|---|---|---|
| O entitate `climate` pe cameră (ținta, nivelul, pornit/oprit), pentru asistenții vocali, cardurile de termostat, HomeKit / Google / Alexa | noi | de decis | SHC nu are `climate` pe cameră. Discutat 2026-11-12: `climate.<cameră>_termostat` pe dispozitivul camerei, fără setări noi. Arată temperatura camerei, umiditatea (dacă are senzor), ținta de acum și presetul (nivelul, cu numele camerei). Moduri: *auto* = normal (alegerea lui șterge modificarea manuală), *heat* = e activă o modificare manuală, *off* = cameră oprită (antiîngheț). Temperatura sau presetul setate de acolo = modificare manuală cu durata implicită a casei (ca *Set for a while*, fără buton Set: cardul standard trimite după ce te oprești, o nouă valoare o înlocuiește pe cea veche). Fereastra, pauza și siguranța au prioritate. De stabilit: numele, *off* = antiîngheț sau oprit, cât ține *off* (ca o modificare manuală sau până la *auto*); termostatul SHC exclus din dispozitivele camerelor (buclă). |
| Comutator „controlată de SHC” pe cameră (o cameră lăsată temporar în pace, din automatizări) | noi | de decis | Poate ajunge *off* al termostatului pe cameră, dacă îl facem. |
| Estimarea economiei (ore de încălzire evitate, kWh / cost) | noi | de decis | SHC are deja timpul de funcționare pe casă și pe cameră; o estimare ar fi aproximativă. În lucru (2026-11-27): orele casei pe regulă (plecat, cameră goală, oprire anticipată, fereastră) și comparația cu perioada trecută după vreme, fără kWh și fără bani. |
| Reglarea directă a deschiderii ventilului (%) | noi | nu facem | Reglează aparatul în locul lui: în afara principiului. |
| Prezență din entități care nu sunt `person` (input_boolean, alarmă) | noi | există deja | Modul *Away* al casei se poate seta dintr-o automatizare; în camere, senzorii de ocupare. |
| Temperatura resimțită pe cameră (umiditatea, eventual temperatura radiantă) | idee de la utilizator (2026-11-12) | de decis | Calculat cu PMV (ISO 7730): la temperaturi de casă umiditatea contează puțin (21 °C: 35% → 20,6 °C, 55% → 21,1 °C); efectul față de 50% variază cu cel mult ±0,15 °C pentru haine 0,7–1,3 clo și activitate 1,0–1,4 met, deci fără setări: resimțit = T + (umiditate − 50) × (0,025 + 0,0015 × (T − 21)). Formulele meteo (Apparent Temperature, Heat Index) exagerează în casă. Temperatura radiantă (pereți reci la 18 °C: −1,4 °C) nu se poate măsura fără senzor special: nu intră. Doar informativ, doar cu senzor de umiditate: senzor *Resimțit* pe cameră, atribut pe termostat (nu există câmp standard), în card lângă temperatură, umiditate și țintă. Nu schimbă ținta. |
| Echilibrarea camerelor (camere care se încălzesc mult mai greu decât altele) | idee de la utilizator (2026-11-12) | de decis | Sincronizarea confortului există deja: pornirea optimă pornește fiecare cameră după viteza ei învățată (livingul cu 40 min înainte, dormitorul cu 100). Împărțirea căldurii prin deschideri parțiale = echilibrare hidraulică / control procentual: nu facem. Idee rămasă: diagnostic din viteza învățată („dormitorul se încălzește de 2,5 ori mai încet decât restul casei: aerisire, robinetul de retur, calorifer mic”), ca alerta de diferență între camere, dar din învățare. |
| Control procentual al ventilului TRV (deschidere %) | discutat 2026-11-12 | nu facem | Ar face din SHC regulatorul (în afara principiului); risc dacă HA cade (TRV cu țintă mare și ultimul procent), baterie, fiecare TRV altfel; calibrarea cu senzor extern dă deja cea mai mare parte. |

## Din analiza de interfață și psihologie (2026-11-27)

Analiză a proiectelor de încălzire asemănătoare, a ghidului de design Home Assistant (carduri cu o acțiune principală clară, „features” pe cardul tile, Material 3) și a principiilor despre utilizatori (feedback detaliat, comparația cu propriul trecut, gradientul țintei, regula peak-end, legea lui Hick, tehnologia calmă). În lucru din ea: orele pe regulă, comparația după vreme și momentul de reușită al pornirii optime.

| Idee | Principiul | Stare | Note |
|---|---|---|---|
| Simulator „−1 °C” pe cameră | feedback concret | de decis | Cât ar scădea încălzirea camerei cu un grad mai puțin, din modelul învățat (încălzire, pierderi, curba vremii), nu din istoric. Doar pentru camerele învățate. |
| Camerele comparate pe m² | comparație între camere | de decis | Atributul `area` există; statisticile împart timpul doar procentual. Pe m² se vede camera care pierde căldură (izolație). |
| Casa „calmă”: un singur rând liniștit când totul e în regulă | tehnologia calmă | de decis | Iese în față doar ce cere atenție (alerte, fereastră, pauză). |
| SHC ca „feature” pe cardul tile din Home Assistant (nivelul, „temporar”) | legea lui Jakob | de decis | Pentru cine nu vrea cardul mare; cardurile tile suportă controale rapide prin „features”. |
| Rezumat săptămânal opțional, prin notificare | feedback, tehnologia calmă | de decis | Un singur mesaj pe săptămână: orele pe regulă și comparația după vreme. |
| Diagnoza din învățare (o cameră se încălzește mult mai încet decât a învățat) | feedback | de decis | Aceeași idee ca la *Echilibrarea camerelor* de mai sus; pragul de discutat. |
| Butoanele camerei: trei vizibile (Temporar, Program, Grafic), restul sub „Mai mult” | legea lui Hick | de decis | Doar dacă șase butoane par prea multe. |
| Partea vizuală: duratele animațiilor, tema închisă și tab-ul Istoric, dimensiunile în grila Sections | ghid de design | mai târziu | Animațiile: scurte (~300 ms) pentru tranziții funcționale, ~650 ms pentru cele expresive (arcul e deja așa). Grila Sections: rând de 56 px, spațiu de 8 px. |
| Frunză „eco”, serii, insigne | — | nu facem | Moralizează și transformă încălzirea în joc. |
| Slider confort / eficiență | — | nu facem | Histerezisul, inerția și oprirea anticipată fac deja asta, cu sens clar. |
| Comparația cu alte case | — | nu facem | SHC nu are și nu trebuie să aibă date din afara casei. |

