# Ghidul complet Smart Heating Control

*[English](README.md)*

Acest ghid explică **toată integrarea**: ce face, cum se configurează pas cu
pas și cum ia deciziile. Este scris și pentru cine nu e specialist și vrea doar
ca încălzirea să meargă singură. Termenii tehnici sunt explicați prima dată
când apar, iar fiecare capitol are exemple.

Dacă vrei doar să pornești repede, citește capitolele 1, 2 și 3. Restul îl poți
citi când ai nevoie de o funcție anume.

Ca să configurezi pas cu pas, cu o explicație pentru fiecare alegere, folosește
[configuratorul interactiv](../configurator.html) (descarcă-l și deschide-l
într-un browser).

## Cuprins

| Capitol | Despre ce e |
| --- | --- |
| [1. Concepte](01-concepte.ro.md) | Ce face integrarea, casa și camerele, nivelurile, decizia și ordinea regulilor |
| [2. Instalarea și casa](02-instalare-si-casa.ro.md) | Instalare, crearea casei, încălzirea întregii case, toate opțiunile casei |
| [3. Camerele](03-camere.ro.md) | Adăugarea unei camere pentru fiecare tip de încălzire (Generic Thermostat, TRV / alte termostate, releu), fiecare pas explicat |
| [4. Programul](04-program.ro.md) | Profiluri, zile, calendar, zile lucrătoare, începutul zilei, Schedule helper |
| [5. Prezența și vacanța](05-prezenta.ro.md) | Acasă / aproape / departe, zone, întârzieri, senzori de prezență, oaspeți, preîncălzirea pe drum spre casă, ocuparea camerei, vacanța |
| [6. Vremea și sezonul](06-vreme.ro.md) | Temperatura de afară, oprirea când e cald, prognoza, sezonul de încălzire, compensarea, câștigul solar |
| [7. Pornirea și oprirea anticipată, învățarea](07-anticipare-si-invatare.ro.md) | Cum învață fiecare cameră cât durează să se încălzească și să se răcească, și cum folosește asta |
| [8. Sursa de căldură și energia](08-sursa-si-energie.ro.md) | Centrala comandată de integrare, camere necesare, camera de referință, timpi minimi, tarif, fotovoltaic, timpul de încălzire |
| [9. Ferestre, modificări manuale și siguranță](09-ferestre-manual-siguranta.ro.md) | Ferestre, modificări manuale, blocare pentru copii, pauză, moduri, antiîngheț, maxim, verificarea comenzilor, alerte, mișcarea robinetelor |
| [10. Cardul](10-card.ro.md) | Cardul Lovelace: ce arată, cum se folosește, toate opțiunile |
| [11. Entități, servicii și automatizări](11-entitati-si-servicii.ro.md) | Toate entitățile, serviciile, evenimentul, diagnosticul, exemple de automatizări |
| [12. Exemple și întrebări](12-exemple-si-intrebari.ro.md) | Configurări complete pentru case obișnuite, întrebări frecvente, ce faci când ceva nu merge |

## Alte documente

- [Specificația](../SPEC.ro.md): toate regulile și valorile implicite, pe scurt, în tabele.
- [Cum învață integrarea](../learning.ro.md): matematica învățării, cu calcule complete și simulări.

## Cum să citești exemplele

Numerele din exemple sunt de două feluri, iar textul spune mereu care e care:

- **valori implicite** ale integrării (de exemplu antiînghețul de 7 °C): sunt
  cele pe care le primești dacă nu schimbi nimic;
- **valori alese pentru exemplu** (de exemplu „ținta de 21 °C”): sunt puse doar
  ca să se vadă calculul; la tine pot fi altele.

Când un exemplu face un calcul, calculul e scris complet.

Numele setărilor sunt date ca în interfața în română, iar în paranteză, unde
ajută, numele din interfața în engleză.
