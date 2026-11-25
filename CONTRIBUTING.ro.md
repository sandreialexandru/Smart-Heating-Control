# Contribuții

*English: [CONTRIBUTING.md](CONTRIBUTING.md)*

- **O eroare**: un issue cu formularul *Bug report*. Issue-urile sunt doar
  pentru erori.
- **O întrebare despre configurare**: în
  [discuțiile Q&A](https://github.com/sandreialexandru/Smart-Heating-Control/discussions/categories/q-a).
- **O idee sau o cerere de funcție**: în
  [discuțiile Ideas](https://github.com/sandreialexandru/Smart-Heating-Control/discussions/categories/ideas),
  unde și alții pot vota și pot spune cum le-ar folosi în configurația lor.
- **O traducere**: în [issue-ul #12](https://github.com/sandreialexandru/Smart-Heating-Control/issues/12)
  sau ca pull request.

## Cum se decid cererile de funcții

Smart Heating Control e făcut să funcționeze la fel în orice casă: un singur
set de reguli, testate împreună, care comandă încălzirea prin entitățile
climate și ajutătoarele existente. Fiecare opțiune adăugată apare în setările
tuturor și e încă o combinație care trebuie să funcționeze cu toate celelalte,
la fiecare versiune.

De aceea o cerere se cântărește după trei întrebări:

- **Ajută multe case sau o singură configurație?** O nevoie legată de un
  dispozitiv, de o integrare sau de un mod anume de a locui poate fi reală și
  totuși să nu-și aibă locul în nucleu.
- **Se poate face deja?** Multe nevoi particulare sunt acoperite de ce oferă
  SHC: template-ul de ocupare, calendarul, serviciile, evenimentul
  `advanced_climate_decision_changed` și automatizările Home Assistant din
  jurul lor. Răspunsul la o cerere e adesea un exemplu de cum se face.
- **Cât îi costă pe ceilalți?** O schimbare care adaugă complexitate sau risc
  în nucleu, în ordinea regulilor sau în învățare trebuie să aducă destul
  tuturor ca să merite.

Nu intră în scop: monitorizarea sau comanda altor echipamente decât
încălzirea (centrale, contoare, alte integrări) și transformarea panoului
într-un dashboard editabil. Cardul se poate pune pe un dashboard propriu,
lângă orice alt card.

O cerere care nu se preia nu e o judecată asupra nevoii sau a persoanei. Așa
rămâne integrarea sigură pentru toți cei care o folosesc. Voturile și
configurațiile din
[Ideas](https://github.com/sandreialexandru/Smart-Heating-Control/discussions/categories/ideas)
arată câte case ar ajuta o idee.

## Pull requesturi

- **Spre `dev`**, nu spre `main`: `main` conține doar versiunile publicate.
- **O funcție nouă se discută întâi** în
  [discuțiile Ideas](https://github.com/sandreialexandru/Smart-Heating-Control/discussions/categories/ideas).
  Se aplică aceleași trei întrebări ca la o cerere, iar un PR se acceptă mai
  ușor când abordarea a fost stabilită înainte de a scrie codul.
- **Corecturile și traducerile sunt binevenite direct.**
- **Ce aduce un PR odată cu el:** teste pentru ce schimbă și un rând în
  secțiunea *Unreleased* din `CHANGELOG.md`. Documentația se actualizează în
  cadrul proiectului; versiunea nu se schimbă într-un PR: se stabilește la
  publicare.
- **Funcționează la fel în orice casă:** fără ramuri pentru un anumit
  dispozitiv sau o anumită configurație, fără limite sau marje nestabilite.
- **Testat în propriul Home Assistant**, nu doar de testele automate.

Un PR care nu se preia nu e o judecată asupra muncii: se aplică aceleași
motive ca la o cerere.
