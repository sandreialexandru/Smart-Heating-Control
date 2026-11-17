<img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/custom_components/advanced_climate/brand/icon@2x.png" alt="Smart Heating Control" width="128" align="right">

# Smart Heating Control

[English](README.md) | **Română** | [Deutsch](README.de.md) | [Nederlands](README.nl.md) | [Français](README.fr.md) | [Italiano](README.it.md)

[![Home Assistant Marketplace Default](https://img.shields.io/badge/Home%20Assistant%20Marketplace-Default-41BDF5.svg?logo=homeassistant&logoColor=white)](https://hacs.xyz/)
[![Validate](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml)
[![Tests](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml)

**Îți place Smart Heating Control? Susține dezvoltarea lui:**

<a href="https://ko-fi.com/sandreialexandru"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support on Ko-fi" height="44"></a>

**Încălzire pentru Home Assistant care știe cine e acasă, învață cum se
încălzește fiecare cameră și spune de ce face ce face.**

Cald la venirea acasă, mai rece când nu e nimeni, fără căldură irosită pe o
fereastră deschisă și fără reguli de scris. Funcționează cu ce există deja:
Generic Thermostat, TRV-uri, termostate inteligente sau un simplu releu.

<p align="center"><a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-demo.gif" alt="Cardul în folosire · persoane și date inventate" width="440"></a></p>

<p align="center"><sub>Cardul în folosire · persoane și date inventate · <a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7">video-ul la calitate mai bună</a></sub></p>

## Ce face

**Știe cine e acasă.** Fiecare persoană e *acasă*, *aproape* (undeva în
oraș) sau *departe*. Casa încălzește pentru cine e acolo, ține *eco* cât
cineva e doar aproape, trece pe *away* când toți sunt departe și, cu Proximity
(recomandat, cu direcția) sau cu un senzor de timp de drum, pornește din nou
încălzirea când cineva e pe drum spre casă.

**Învață singură fiecare cameră.** Fiecare cameră învață cât de repede se
încălzește, cum se răcește, cât de încet reacționează caloriferele sau
pardoseala, cât dă în plus la ger o centrală cu curbă de temperatură și, cu o
entitate meteo, cât o încălzește soarele. Apoi pornește încălzirea exact cât
de devreme trebuie ca să fie cald la timp și o oprește mai devreme când camera
rămâne oricum confortabilă. Nu se setează nimic: unei camere îi trebuie circa
o zi, 4 ore cu încălzire și 4 fără.

**Programe după săptămâna fiecăruia.** Profiluri pentru zile lucrătoare,
weekend, zile anume sau sărbători (din integrarea Workday), un calendar care
alege profilul unei zile sau un helper Program existent. Se editează în card,
prin tragerea orelor.

**Ferestre deschise și modificări manuale, rezolvate.** Un senzor de
fereastră sau o scădere bruscă a temperaturii reduce încălzirea; camerele
vecine pot urma. O modificare făcută de mână pe termostat se păstrează cât
s-a ales, apoi revine programul.

**Ține cont de vreme.** Oprește încălzirea când e cald afară (și după
prognoză), păstrează un sezon de încălzire, adaugă căldură la ger și coboară
ținta unei camere însorite.

**Energie.** Pornește centrala doar când o cameră are nevoie, urmează un
tarif dinamic sau surplusul fotovoltaic, trece pe o a doua sursă de căldură
(pompa cât e soare, centrala când e foarte frig) și numără timpul de
încălzire pe zi, săptămână sau lună.

**Sigură.** Antiîngheț mereu, o temperatură maximă, fiecare comandă
verificată și trimisă din nou dacă n-a ajuns, alerte pentru ferestre deschise,
dispozitive indisponibile, baterii descărcate și **risc de mucegai** la
peretele cel mai rece, plus mișcarea săptămânală a robinetelor TRV.

**Se explică singură.** Fiecare cameră are un senzor *Decizie* cu regula
care a câștigat și motivul, un eveniment la fiecare schimbare și un diagnostic
cu ultimele 100 de decizii.

**Se potrivește casei.** Generic Thermostat (se alege doar presetul;
termostatul funcționează la fel ca înainte), TRV-uri cu calibrare după un
senzor din cameră, alte termostate, relee. °C sau °F pe casă. În română,
engleză, germană, olandeză, franceză și italiană.

## Cardul

Integrarea vine cu un card Lovelace, adăugat singur la resursele
dashboard-ului.

<table>
  <tr>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-hero.png" alt="Casa cu persoanele, modul și butoanele, o cameră deschisă și celelalte camere pliate" width="360"><br><sub>Casa și camerele</sub></td>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-details.png" alt="Detaliile camerei: temperaturi, umiditate, următoarea oprire anticipată și ce a învățat camera" width="360"><br><sub>Ce a învățat o cameră</sub></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-chart.png" alt="Graficul: temperatura, ținta, încălzirea, temperatura de afară și temperatura prezisă" width="720"><br><sub>7 zile de istoric și următoarele 12 ore, cu temperatura pe care o așteaptă camera</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-light.png" alt="O modificare manuală cu secțiunea Setează temporar deschisă, temă deschisă" width="360"><br><sub>Un nivel sau o temperatură pentru o vreme</sub></td>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-compact.png" alt="Cardul compact: o placă pe cameră" width="360"><br><sub>Compact: o placă pe cameră</sub></td>
  </tr>
</table>

```yaml
type: custom:smart-heating-control-card
```

Orice parte se poate ascunde; opțiunile sunt în [ghid](docs/guide/10-card.ro.md).

## Panoul

O pagină proprie în bara laterală, **SHC**, pentru toți utilizatorii: toată
casa pe un ecran, programul tuturor camerelor pentru săptămâna care urmează
(copiat în alte camere dintr-o atingere), statistici (timpul de încălzire și
temperaturile pe zile, săptămâni sau luni, și când încălzește fiecare cameră,
oră cu oră), istoricul deciziilor și al alertelor cu alertele active sus,
umiditatea camerelor cu riscul de mucegai și toate dispozitivele camerelor cu
bateria lor. Nu cere nicio setare; detaliile sunt în
[ghid](docs/guide/13-panou.ro.md).

<table>
  <tr>
    <td colspan="2" align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/panel-rooms.png" alt="Toată casa pe un ecran, camerele grupate pe etaje · persoane și date inventate" width="720"><br><sub>Toată casa pe un ecran, camerele grupate pe etaje</sub></td>
  </tr>
  <tr>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/panel-schedule.png" alt="Săptămâna care urmează a fiecărei camere, cu calendarul · persoane și date inventate" width="360"><br><sub>Săptămâna care urmează a fiecărei camere, cu calendarul</sub></td>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/panel-stats.png" alt="Timpul de încălzire față de temperatura de afară · persoane și date inventate" width="360"><br><sub>Timpul de încălzire față de temperatura de afară</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/panel-heatmap.png" alt="Când încălzește fiecare cameră, oră cu oră · persoane și date inventate" width="360"><br><sub>Când încălzește fiecare cameră, oră cu oră</sub></td>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/panel-devices.png" alt="Umiditatea și riscul de mucegai, fiecare dispozitiv cu bateria lui · persoane și date inventate" width="360"><br><sub>Umiditatea și riscul de mucegai, fiecare dispozitiv cu bateria lui</sub></td>
  </tr>
</table>

<table>
  <tr>
    <td align="center" width="25%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/phone-rooms.png" alt="Pe telefon · persoane și date inventate" width="180"></td>
    <td align="center" width="25%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/phone-room.png" alt="Pe telefon · persoane și date inventate" width="180"></td>
    <td align="center" width="25%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/phone-schedule.png" alt="Pe telefon · persoane și date inventate" width="180"></td>
    <td align="center" width="25%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/phone-heatmap.png" alt="Pe telefon · persoane și date inventate" width="180"></td>
  </tr>
</table>

<p align="center"><sub>Pe telefon · persoane și date inventate</sub></p>

## Primii pași

[![Deschide Home Assistant și adaugă acest repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sandreialexandru&repository=Smart-Heating-Control&category=integration)

1. **Instalează** din **Marketplace** (**Setări → Marketplace**, Home
   Assistant 2026.11 sau mai nou): caută **Smart Heating Control** și
   instalează-l, sau deschide-l cu butonul de mai sus; repornește Home
   Assistant dacă ți se cere. Înainte de 2026.11 se face la fel în HACS, urmat
   de o repornire. Fără ele, copiază `custom_components/advanced_climate` în
   `config/custom_components` și repornește.
2. **Casa**: **Settings → Devices & services → Add integration → Smart Heating
   Control**, sau acest buton:

   [![Deschide Home Assistant și adaugă Smart Heating Control](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=advanced_climate)

   Se aleg persoanele și termostatul care încălzește casa; pentru o casă cu
   un singur termostat, asta e tot.
3. **Camerele** (opțional), cele cu robinete sau termostate proprii, se adaugă
   din pagina integrării, iar cardul se pune pe un dashboard.

Necesită Home Assistant **2026.6.0** sau mai nou.

<a href="https://github.com/sandreialexandru/Smart-Heating-Control/blob/main/docs/configurator.html"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/configurator.png" alt="Configuratorul: fiecare alegere explicată, cu ce schimbă și un exemplu" width="420" align="right"></a>

**Nu e clar ce trebuie ales?** [Configuratorul interactiv](https://github.com/sandreialexandru/Smart-Heating-Control/blob/main/docs/configurator.html)
începe cu ce încălzește locuința și completează răspunsurile potrivite, apoi
trece prin fiecare formular, în română sau engleză, explică fiecare alegere cu
ce schimbă și un exemplu și se încheie cu un rezumat a ce trebuie setat și cu
problemele găsite (de exemplu un dispozitiv cu două roluri).
Fișierul se descarcă și se deschide într-un browser.

<br clear="right">

## Documentație

| Document | Ce conține |
|---|---|
| [Ghid](docs/guide/README.ro.md) | Pas cu pas, pe înțelesul tuturor: fiecare setare, fiecare fel de încălzire, exemple |
| [Testat cu](docs/tested-with.ro.md) | Dispozitivele confirmate de utilizatori |
| [Cum învață integrarea](docs/learning.ro.md) | Modelul camerei, cu exemple calculate și simulări |
| [Referință](docs/reference.ro.md) | Fiecare regulă, senzor, atribut, serviciu și opțiune a cardului, în detaliu tehnic |
| [Specificație](docs/SPEC.ro.md) | Specificația completă |
| [Changelog](CHANGELOG.md) | Ce s-a schimbat, versiune cu versiune (în engleză) |

## Traduceri

Integrarea și cardul: română, engleză, germană, olandeză, franceză și italiană. Documentația: română și engleză.

Textele în germană, olandeză, franceză și italiană sunt noi: dacă vorbești una dintre ele, ajută la verificarea lor în [acest issue](https://github.com/sandreialexandru/Smart-Heating-Control/issues/12).

## Susținere

Dacă Smart Heating Control e de folos, proiectul poate fi susținut cu o cafea
pe [Ko-fi](https://ko-fi.com/sandreialexandru). Mulțumesc!

## Licență

MIT
