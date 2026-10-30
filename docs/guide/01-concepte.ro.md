# 1. Concepte

*[English](01-concepts.md) · [Cuprins](README.ro.md)*

## Ce face integrarea, pe scurt

Smart Heating Control hotărăște **cât de cald trebuie să fie în fiecare
cameră** și le spune dispozitivelor de încălzire (termostate, robinete
termostatice, relee) ce să facă. Ține cont de:

- **program**: de exemplu 21 °C ziua, 18 °C noaptea;
- **cine e acasă**: când pleacă toată lumea, casa se răcește singură, iar când
  vine cineva, se încălzește din nou;
- **ferestre**: o fereastră deschisă oprește sau reduce încălzirea camerei;
- **vreme**: când e cald afară, încălzirea se oprește;
- **modificările de mână**: dacă temperatura e schimbată pe termostat,
  integrarea respectă schimbarea un timp;
- **siguranță**: casa nu îngheață niciodată și nu se supraîncălzește.

Integrarea nu înlocuiește termostatul existent. Cu **Generic
Thermostat** (termostatul generic din Home Assistant), el continuă să
funcționeze exact ca înainte; integrarea doar îi alege presetul potrivit
(„acasă”, „somn”, „plecat”…).

## Casa și camerele

Configurarea are două niveluri:

- **Casa** este o singură intrare a integrării. Ea ține lucrurile comune:
  persoanele, zonele, modul global (Auto / Vacanță / Oprit / Vară), vremea,
  centrala, alertele.
- **Camerele** sunt adăugate în casă. Fiecare cameră are dispozitivele ei,
  senzorii ei, ferestrele ei și programul ei.

La crearea casei se alege și **încălzirea întregii case**: de obicei termostatul
care pornește centrala. El devine zona **Whole house** (toată casa), care se
comportă ca o cameră. Pentru un apartament încălzit de un singur termostat,
asta e tot ce trebuie: nu se mai adaugă nicio cameră.

Camere separate se adaugă doar pentru camerele cu robinete sau termostate proprii
(de exemplu TRV-uri, adică robinete termostatice pe calorifere).

**Exemplu.** Un apartament cu centrală pe gaz și un singur termostat în
sufragerie: se creează casa, se alege termostatul la *Încălzirea întregii case*
și gata. O casă cu TRV-uri în fiecare cameră: se creează casa (se poate alege
*Încă fără dispozitive*), apoi se adaugă câte o cameră pentru fiecare cameră cu
TRV.

## Nivelurile (preseturile)

În loc să lucreze direct cu temperaturi, integrarea lucrează cu **niveluri**.
Fiecare nivel are o temperatură, iar unele niveluri au un **rol fix**:

| Nivel | Rol | Temperatura implicită (camere fără Generic Thermostat) |
| --- | --- | --- |
| `home` (acasă) | cineva e acasă, ziua | 21 °C |
| `sleep` (somn) | noaptea, cu cineva acasă | 18 °C |
| `eco` | nimeni acasă, dar cineva e prin apropiere (de exemplu în oraș) | 17 °C |
| `away` (plecat) | toată lumea e departe, sau vacanță | 12 °C |
| `comfort` | fără rol automat; se folosește în program | 22 °C |
| `activity` | fără rol automat; se folosește în program | 20 °C |

Numele vin de la presetările Generic Thermostat. La o cameră cu Generic
Thermostat, temperaturile sunt cele setate în GT; integrarea doar alege
presetul. La celelalte camere temperaturile se setează în integrare, iar
numele nivelurilor pot fi schimbate (de exemplu „Zi” în loc de `home`).

Pe lângă niveluri mai există două limite:

- **antiînghețul** (implicit 7 °C, sau temperatura minimă a Generic
  Thermostat): cea mai mică temperatură pe care o primește vreodată o cameră;
- **temperatura maximă** (implicit 25 °C): nicio țintă nu trece de ea.

## Decizia

Pentru fiecare cameră integrarea calculează mereu **o singură decizie**: ce
regulă se aplică acum și ce țintă rezultă. Decizia se vede în senzorul
*Decizie* al camerei și în card, împreună cu motivul. De exemplu:

- *Program: home*;
- *Toți sunt departe (în afara zonelor apropiate)*;
- *Fereastră deschisă: antiîngheț*.

Decizia se recalculează **imediat** ce se schimbă ceva important (o persoană
pleacă, se deschide o fereastră, vine ora din program) și, în plus, periodic
(implicit la 5 minute), ca o verificare de siguranță.

## Ordinea regulilor

Ca două reguli să nu se contrazică niciodată, ele au o **ordine fixă**. Se
verifică de sus în jos, iar prima care se aplică decide:

1. **Siguranță**: antiîngheț și temperatură maximă. Se aplică mereu, chiar și
   peste o modificare manuală sau în pauză.
2. **Pauză**: integrarea trimite doar siguranța.
3. **Mișcarea robinetelor**: o dată pe săptămână TRV-urile se deschid complet
   câteva minute, contra depunerilor.
4. **Mod Oprit / Vară / în afara sezonului**: încălzire oprită (la Oprit, doar
   antiîngheț).
5. **Fereastră deschisă**.
6. **Modificare manuală**.
7. **Vacanță**: `away`.
8. **Prezență**: departe → `away`, aproape → `eco` (sau o temperatură fixă).
9. **Program**: cu pornirea și oprirea anticipată și ocuparea camerei.

După ce o regulă a decis, se aplică **ajustările** (oprirea când e cald afară,
compensarea pentru frig, tariful, fotovoltaicul, câștigul solar), iar la final
rezultatul trece din nou prin **limitele de siguranță**.

**Exemplu.** E ora 10, programul spune `home` (21 °C), dar toată lumea e
plecată, iar în sufragerie e o fereastră deschisă. Regulile 1–4 nu se aplică
(nu e pauză, modul e Auto). Regula 5, fereastra deschisă, se aplică:
sufrageria trece pe antiîngheț. În dormitor, unde fereastra e închisă, se
ajunge la regula 8: toți sunt departe, deci `away`.

O regulă de prezență sau vacanță **nu ridică niciodată** temperatura peste ce
ar fi „normal”: de exemplu, într-o zi fără profil activ în program
(antiîngheț), plecarea nu aduce `away`, care ar fi mai cald, ci rămâne
antiînghețul.

## Unitatea de temperatură

Fiecare casă are o singură unitate, °C sau °F. Toate temperaturile casei se
introduc și se afișează în ea. Termostatele și senzorii pot fi în altă unitate:
integrarea convertește singură. Unitatea se schimbă din *Reconfigurează* pe
pagina integrării, iar valorile se convertesc.

## Termeni folosiți în ghid

| Termen | Ce înseamnă |
| --- | --- |
| Generic Thermostat (GT) | Termostatul generic din Home Assistant: pornește un releu sau o centrală după un senzor de temperatură |
| TRV | Robinet termostatic pe calorifer, comandat prin Zigbee, Z-Wave sau Wi-Fi |
| Releu | Un comutator (`switch` sau `input_boolean`) care pornește direct încălzirea |
| Sursa de căldură | Centrala sau releul care o pornește |
| Histerezis | Cât de mult poate coborî sau urca temperatura în jurul țintei înainte ca releul să pornească sau să se oprească; evită pornirile și opririle dese |
| Toleranță | Cât lasă termostatul camera să coboare sub țintă înainte să încălzească |
| `hvac_action` | Informația pe care o dă un termostat: încălzește acum sau nu |
| Reevaluare | Recalcularea deciziei |
| Antiîngheț | Temperatura minimă de siguranță |
| Pornire anticipată | Încălzirea pornește mai devreme, ca nivelul următor să fie atins exact la ora din program |
| Oprire anticipată | Nivelul mai rece începe mai devreme, cât timp camera rămâne confortabilă până la ora din program |
