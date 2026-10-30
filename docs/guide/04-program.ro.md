# 4. Programul

*[English](04-schedule.md) · [Cuprins](README.ro.md)*

Programul spune **ce nivel se dorește cât timp cineva e acasă**. Prezența,
ferestrele și celelalte reguli îl pot coborî (de exemplu `away` când pleacă
toată lumea), dar nu îl pot ridica.

## Formatul

Un **profil** pe rând. Fiecare interval este `HH:MM nivel` și ține până la
următorul:

```
workday: 00:00 sleep, 06:00 home, 22:00 sleep
weekend: 00:00 sleep, 08:00 home, 23:00 sleep
```

Citire: în zilele lucrătoare `sleep` de la 00:00, `home` de la 06:00, `sleep`
de la 22:00 până la sfârșitul zilei. În weekend ziua începe la 08:00.

Acesta e și programul implicit al fiecărei camere noi.

- Numele profilului e liber (`workday`, `weekend`, `home_office`, `vineri`,
  `sâmbătă`…), și cu diacritice; doar `,` `:` și `#` nu se pot folosi.
- Nivelul poate fi oricare dintre `home`, `sleep`, `eco`, `away`, `comfort`,
  `activity`, sau numele date nivelurilor în setările camerei.
- Dacă primul interval nu începe la 00:00 (sau la începutul zilei, mai
  jos), până la el continuă ultimul nivel al zilei de dinainte. De exemplu, cu
  `workday: 06:00 home, 22:00 sleep`, între 00:00 și 06:00 rămâne `sleep` de la
  22:00 din ziua precedentă.

Un program greșit nu e salvat (*Program invalid*). Dacă un program salvat
devine invalid, camera folosește programul implicit și afișează alerta
*Programul e invalid (…); se folosește programul implicit*.

Cel mai ușor se editează din **card** (*Program*): orele de început se trag pe
bara zilei, în pași de 5 minute, iar un profil se poate copia peste altul
([capitolul 10](10-card.ro.md)).

## Zilele fiecărui profil

Fiecare profil are **zilele lui** și e **pornit sau oprit**. Se setează din
card:

| Zile | Înseamnă |
| --- | --- |
| Toate zilele | fiecare zi |
| Zile lucrătoare | luni–vineri, fără sărbători (cu senzorul Workday) |
| Weekend | sâmbătă, duminică și sărbătorile |
| Zile anume | de exemplu doar vineri, sau luni și miercuri |

**Ce profil folosește o zi**, în această ordine:

1. un **eveniment din calendar** cu numele unui profil (chiar și al unui profil
   oprit);
2. profilul activ pentru **acea zi a săptămânii** (de exemplu un profil pentru
   miercuri e mai important decât cel de zile lucrătoare, dar doar miercurea);
3. profilul activ al **zilelor lucrătoare** sau al **weekendului**;
4. profilul activ pentru **toate zilele**;
5. niciunul: ziua rămâne pe **antiîngheț**, iar camera afișează alerta *Fără
   profil activ în program: …*.

**Profilurile active nu se suprapun.** Pornirea unui profil le oprește pe cele
active cu care s-ar suprapune: „toate zilele” se suprapune cu zilele lucrătoare
și cu weekendul, iar zilele anume se suprapun când au o zi comună. Astfel o zi
nu are niciodată două profiluri. Cardul avertizează înainte ca pornirea sau
oprirea unui profil să lase zile fără profil.

**Exemplu.** Există `workday` (zile lucrătoare), `weekend` (weekend) și
`home_office` (doar miercuri). Miercuri se folosește `home_office`, în celelalte
zile lucrătoare `workday`, sâmbăta, duminica și sărbătorile `weekend`.

## Zile lucrătoare și sărbători

Fără senzor Workday, luni–vineri sunt zile lucrătoare. Cu senzorul integrării
**Workday** (opțiunile casei, *Zile lucrătoare și calendar*), sărbătorile sunt
tratate ca weekend. Integrarea întreabă Workday și despre următoarele 7 zile,
ca planul (și pornirea anticipată) pentru mâine să știe că mâine e sărbătoare.

## Calendarul

Opțional, se poate alege un **calendar** din Home Assistant (de exemplu un calendar
local sau Google). Titlul evenimentului contează:

- **Numele unui profil** (de exemplu `home_office`): profilul se folosește
  pentru **toată ziua** din care evenimentul acoperă o parte. Regula e aceeași
  azi și în zilele următoare, ca planul și pornirea anticipată calculate cu o
  zi înainte să corespundă cu ce se întâmplă.
- **Numele unui nivel** (de exemplu `away` sau `comfort`): nivelul se aplică
  **cât durează evenimentul**, în locul programului.

Evenimentele se citesc de la începutul zilei de azi pe următoarele 7 zile, în
fiecare oră și imediat ce se schimbă calendarul.

**Exemple.**

- Un eveniment de toată ziua „weekend” într-o zi de marți (zi liberă luată):
  marți se folosește profilul `weekend`.
- Un eveniment „weekend” marți 10:00–16:00: tot profilul `weekend`, pentru toată
  ziua de marți.
- Un eveniment „away” vineri 09:00–17:00 (un curs în altă parte): vineri între 09:00 și
  17:00 nivelul e `away`, apoi revine programul.

Regulile de mai sus de program (fereastră, prezență, siguranță) se aplică și
peste calendar.

## Începutul zilei (ture de noapte)

*Ziua programului începe la* (implicit 00:00) mută momentul în care se schimbă
ziua programului.

**Exemplu.** Cineva lucrează în ture de noapte și se culcă vineri dimineața la
04:00.
Cu începutul zilei la 05:00, intervalul de vineri 00:00–05:00 aparține încă
zilei de joi: se folosește profilul de joi (zi lucrătoare) până la 05:00, nu cel
de vineri.

## Schimbarea orei

Programul folosește ora locală, dar ține cont de momentul real:

- **toamna**, când ora 03:00–04:00 se repetă, un interval din acea oră (de exemplu
  `03:30 home`) se aplică **o singură dată**, la prima apariție; a doua oară
  camera nu se întoarce la nivelul de dinainte;
- **primăvara**, când ora 03:00–04:00 nu există, un interval din ea (`03:30`)
  începe la **04:00**, iar pornirea anticipată se calculează pentru 04:00.

## Schedule helper

În loc de programul intern se poate folosi un **Schedule helper** al Home
Assistant (*Setări → Dispozitive și servicii → Ajutoare → Program*). Integrarea
folosește un nivel cât helperul e pornit (implicit `home`) și altul cât e oprit
(implicit `sleep`).

E potrivit când există deja un astfel de helper. Programul intern e mai bogat
(mai multe niveluri, profiluri pe zile, editor în card).

## Ce se întâmplă la ora unei schimbări

La ora din program, camera trece pe nivelul nou. Cu **pornirea anticipată**,
încălzirea poate începe mai devreme, ca nivelul nou să fie atins exact la ora
din program; cu **oprirea anticipată**, un nivel mai rece poate începe mai
devreme ([capitolul 7](07-anticipare-si-invatare.ro.md)).

Senzorul *Următoarea schimbare* al camerei arată următoarea schimbare, iar cardul arată
în grafic ce urmează în următoarele 12 ore.

## Schimbarea programului dintr-o automatizare

Serviciul `advanced_climate.set_schedule` înlocuiește programul unei camere
([capitolul 11](11-entitati-si-servicii.ro.md#servicii)):

```yaml
action: advanced_climate.set_schedule
data:
  room: Dormitor
  schedule: |
    workday: 00:00 sleep, 06:30 home, 22:30 sleep
    weekend: 00:00 sleep, 09:00 home, 23:30 sleep
```
