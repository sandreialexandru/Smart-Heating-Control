# 12. Exemple și întrebări

*[English](12-examples-and-faq.md) · [Cuprins](README.ro.md)*

## Configurări complete

### A. Apartament cu centrală și un Generic Thermostat

**Ce există:** o centrală pe gaz pornită de un releu, un Generic Thermostat în
sufragerie, doi locuitori cu aplicația Home Assistant pe telefon.

1. Se creează casa: persoanele, zona orașului ca *zonă apropiată*, *Cel puțin o
   persoană e acasă*.
2. *Încălzirea întregii case*: Generic Thermostat, entitatea lui.
3. În Generic Thermostat se setează preseturile (de exemplu `home_temp` 21,
   `sleep_temp` 18, `eco_temp` 17, `away_temp` 15).
4. Opțiuni → *Vreme și sezon*: entitatea meteo, *Oprește încălzirea când e cald
   afară*, sezonul *Între date*.
5. Zona *Whole house* → *Reconfigurează camera*: senzorul ferestrei, programul,
   *Pornire anticipată*.

**Ce se întâmplă într-o zi lucrătoare** (cu programul implicit
`workday: 00:00 sleep, 06:00 home, 22:00 sleep`):

| Ora | Ce se întâmplă |
| --- | --- |
| 04:50 | Pornirea anticipată pornește centrala (de exemplu cu 70 de minute învățate înainte de 06:00) |
| 06:00 | `home`, sufrageria e deja la 21 °C |
| 08:10 | Ultimul pleacă la 08:00; după întârzierea de 10 minute casa e *aproape* (în oraș): `eco` |
| 17:30 | Cineva vine acasă: `home` |
| 22:00 | `sleep` |

*Sursa de căldură* rămâne goală: Generic Thermostat pornește deja centrala.

### B. Casă cu TRV-uri în fiecare cameră

**Ce există:** o centrală cu un releu Shelly în Home Assistant, TRV-uri Zigbee în
dormitor, sufragerie și birou, senzori de fereastră.

1. Se creează casa, *Încălzirea întregii case*: *Încă fără dispozitive*.
2. Se adaugă câte o cameră: *Alte termostate / TRV-uri*, comanda *Temperatură*,
   nivelurile, senzorul de fereastră; opțional un senzor pe perete cu
   calibrare *Offset*; mișcarea robinetelor.
3. Opțiuni → *Sursa de căldură și cererea de căldură*: *Sursa de căldură* =
   releul Shelly al centralei; *Camere necesare* 1.

Acum, când un TRV cere căldură, integrarea pornește centrala; când nu mai cere
niciunul, o oprește (cu timpii minimi de 5 minute).

### C. Încălzire electrică cu prize smart și fotovoltaic

**Ce există:** radiatoare electrice pe prize smart, senzori de temperatură în fiecare
cameră, panouri fotovoltaice cu senzor de putere exportată.

1. Fiecare cameră: *Comutator (releu)*, priza, histerezis 0,3 °C, timpi minimi
   0, senzorul camerei (obligatoriu).
2. Opțiuni → *Energie*: senzorul de surplus, *Surplus de la* 1000 W, *Ajustare
   cu surplus* +1 °C.

Ziua, cu soare, camerele urcă cu 1 °C (de exemplu 21 + 1 = 22 °C) din energia
proprie, iar seara consumă mai puțin.

### D. Ture de noapte

Cineva lucrează noaptea de luni până joi și doarme dimineața.

1. Opțiuni → *Zile lucrătoare și calendar*: *Ziua programului începe la*
   05:00.
2. Programul: `workday: 05:00 sleep, 14:00 home` și `weekend: 05:00 home`.

Ziua programului începe acum la 05:00. Vineri între 00:00 și 05:00 (încă în
tură) se folosește ziua de joi, adică profilul `workday` cu `home` de la 14:00.
La 05:00 începe ziua de vineri: somn (`sleep`) până la 14:00.

## Întrebări frecvente

**Trebuie adăugate camere?**
Nu, cu un singur termostat. Zona *Whole house* e suficientă. Camerele se adaugă
doar pentru camerele cu robinete sau termostate proprii.

**Se poate schimba temperatura de mână?**
Da. Integrarea o recunoaște ca modificare manuală și o păstrează (implicit 2
ore). Cu *Blocare modificări* pornit, schimbarea e anulată imediat.

**De ce nu pornește încălzirea?**
Primul pas e decizia camerei în card. Dacă e sub țintă și nu încălzește, cardul
spune motivul (*Nu încălzește: …*). Motive dese: fereastră deschisă, cald afară,
pauză, modul Vară, în afara sezonului, timpul minim, alte camere necesare.

**De ce camera e pe `eco` deși e cineva acasă?**
De verificat senzorul *Prezență*: poate un telefon raportează greșit (atunci
casa e *aproape*). Sau camera are senzori de ocupare și nu a detectat pe nimeni
de *Eco după lipsă de ocupare de* minute.

**Un nivel foarte mic în Generic Thermostat, dar camera stă mai cald.**
Nicio țintă nu poate fi sub antiîngheț. La Generic Thermostat antiînghețul e
`min_temp` al lui; pentru mai puțin, se coboară acolo.

**Pornirea anticipată pornește prea devreme sau prea târziu.**
În primele zile camera învață (până atunci folosește 60 de minute pe grad). După o
schimbare la încălzire, învățarea se poate reseta. Dacă sursa așteaptă alte
camere, așteptarea nu se învață ([capitolul 7](07-anticipare-si-invatare.ro.md)).

**Oprirea anticipată se anulează des.**
Camera se răcește mai repede decât a învățat (de exemplu ușa deschisă).
Ajută micșorarea *Opririi anticipate maxime*.

**Încălzirea s-a oprit într-o zi de toamnă însorită.**
E oprirea când e cald: media pe *Medie pe* ore a ajuns la prag. Ajută mărirea
*Medie pe* sau a pragului, sau pornirea *Folosește prognoza*, ca încălzirea să poată porni
când vine frigul.

**Casa e pe antiîngheț fără un motiv vizibil.**
Poate e o zi fără profil activ în program (camera arată alerta *Fără profil activ
în program*), modul Oprit, o fereastră deschisă sau o fereastră detectată din
scăderea temperaturii.

**Ce se întâmplă dacă Home Assistant repornește?**
Aproape totul se păstrează; nu se păstrează doar limitele TRV învățate de pe
dispozitiv ([capitolul 9](09-ferestre-manual-siguranta.ro.md#repornirea-home-assistant)).

**Merge cu mai multe case?**
Da, fiecare casă e o intrare separată a integrării. Serviciile casei cer atunci
`config_entry_id`.

**Merge pentru răcire (aer condiționat)?**
Nu. Integrarea e pentru încălzire.

## Ce e de făcut când ceva nu merge

1. **Decizia** camerei în card (regula și motivul).
2. ***Detaliile*** camerei: alertele sunt primele.
3. **Entitățile**: senzorii de temperatură, termostatul, persoanele,
   sursa de căldură; una indisponibilă explică multe.
4. **Butonul *Reevaluează*** (casa), ca decizia să fie recalculată imediat.
5. **Diagnosticul** (pagina integrării, ⋮), atașat la raportarea unei probleme
   pe GitHub: are configurația și ultimele 100 de decizii.
