<img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/custom_components/advanced_climate/brand/icon@2x.png" alt="Smart Heating Control" width="128" align="right">

# Smart Heating Control

[English](README.md) | [Română](README.ro.md) | [Deutsch](README.de.md) | [Nederlands](README.nl.md) | [Français](README.fr.md) | **Italiano**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/validate.yml)
[![Tests](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml/badge.svg)](https://github.com/sandreialexandru/Smart-Heating-Control/actions/workflows/tests.yml)

**Ti piace Smart Heating Control? Sostieni il suo sviluppo:**

<a href="https://ko-fi.com/sandreialexandru"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support on Ko-fi" height="44"></a>

**Un riscaldamento per Home Assistant che sa chi è in casa, impara come si
scalda ogni stanza e ti dice perché fa quello che fa.**

Caldo quando torni, più fresco quando non c'è nessuno, niente calore sprecato
da una finestra aperta e nessuna regola da scrivere. Funziona con quello che
hai già: Generic Thermostat, valvole termostatiche, termostati smart o un
semplice relè.

<p align="center"><a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-demo.gif" alt="La scheda in uso · persone e dati inventati" width="440"></a></p>

<p align="center"><sub>La scheda in uso · persone e dati inventati · <a href="https://github.com/user-attachments/assets/31181198-e0fa-4510-bbfa-af9f790a19c7">il video in qualità migliore</a></sub></p>

## Cosa fa

**Sa chi è in casa.** Ogni persona è *a casa*, *vicino* (da qualche parte
nella tua città) o *lontano*. La casa scalda per chi c'è, resta su *eco*
finché siete solo nei paraggi, passa ad *away* quando tutti sono lontani e,
con Proximity (consigliato, con la direzione) o un sensore del tempo di
viaggio, ricomincia a scaldare quando qualcuno sta tornando.

**Impara da sola ogni stanza.** Ogni stanza impara quanto velocemente si
scalda, come si raffredda, quanto lentamente reagiscono i termosifoni o il
pavimento radiante, quanto una caldaia con curva climatica dà di più col
freddo e, con un'entità meteo, quanto la scalda il sole. Poi inizia a
scaldare quanto basta per essere calda in orario, e si ferma prima quando la
stanza resterà comunque confortevole. Niente da impostare: a una stanza serve
circa un giorno, 4 ore con il riscaldamento e 4 senza.

**Programmi su misura per la tua settimana.** Profili per i giorni
lavorativi, il fine settimana, singoli giorni o i festivi (dall'integrazione
Workday), un calendario che sceglie il profilo di un giorno, o un aiutante
Programma esistente. Si modificano nella scheda trascinando gli orari.

**Finestre aperte e modifiche manuali, gestite.** Un sensore della finestra o
un calo improvviso di temperatura abbassa il riscaldamento; le stanze vicine
possono seguire. Giri a mano un termostato e la modifica resta per il tempo
che hai scelto, poi torna il programma.

**Attenta al meteo.** Spegne il riscaldamento quando fuori fa caldo (anche in
base alle previsioni), gestisce una stagione di riscaldamento, aggiunge calore
col gelo intenso e abbassa una stanza al sole.

**Energia.** Accende la caldaia solo quando una stanza ne ha bisogno, segue
una tariffa dinamica o il surplus fotovoltaico e conta il tempo di
riscaldamento per giorno, settimana o mese.

**Sicura.** Sempre l'antigelo, una temperatura massima, ogni comando
controllato e rinviato se non è arrivato, avvisi per finestre aperte,
dispositivi non disponibili, batterie scariche e **rischio muffa** sulla
parete più fredda, e un movimento settimanale delle valvole termostatiche.

**Si spiega da sola.** Ogni stanza ha un sensore *Decisione* con la regola
che ha vinto e il motivo, un evento a ogni cambio e una diagnostica con le
ultime 100 decisioni.

**Si adatta alla tua casa.** Generic Thermostat (si sceglie solo il preset;
il tuo termostato funziona come prima), valvole termostatiche calibrate da un
sensore della stanza, altri termostati, relè. °C o °F per casa. In italiano,
inglese, rumeno, tedesco, olandese e francese.

## La scheda

Con l'integrazione arriva una scheda Lovelace, che si aggiunge da sola alle
risorse della dashboard.

<table>
  <tr>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-hero.png" alt="La casa con le persone, la modalità e i pulsanti, una stanza aperta e le altre chiuse" width="360"><br><sub>La casa e le sue stanze</sub></td>
    <td align="center" width="50%"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-details.png" alt="Dettagli di una stanza: temperature, umidità, il prossimo spegnimento ottimale e cosa ha imparato la stanza" width="360"><br><sub>Cosa ha imparato una stanza</sub></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-chart.png" alt="Il grafico: temperatura, obiettivo, riscaldamento, temperatura esterna e temperatura prevista" width="720"><br><sub>7 giorni di cronologia e le prossime 12 ore, con la temperatura che la stanza si aspetta</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-light.png" alt="Una modifica manuale con la sezione Imposta temporaneamente aperta, tema chiaro" width="360"><br><sub>Impostare un livello o una temperatura temporaneamente</sub></td>
    <td align="center"><img src="https://raw.githubusercontent.com/sandreialexandru/Smart-Heating-Control/main/docs/images/card-compact.png" alt="Scheda compatta: un riquadro per stanza" width="360"><br><sub>Compatta: un riquadro per stanza</sub></td>
  </tr>
</table>

```yaml
type: custom:smart-heating-control-card
```

Ogni parte si può nascondere; le opzioni sono nella
[guida](docs/guide/10-card.md) (in inglese).

## Per iniziare

[![Apri il tuo Home Assistant e aggiungi questo repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sandreialexandru&repository=Smart-Heating-Control&category=integration)

1. **Installa** da HACS (il **Marketplace** da Home Assistant 2026.11):
   cerca **Smart Heating Control**, installalo e riavvia Home Assistant. Non
   lo trovi nella ricerca? Aprilo con il pulsante qui sopra, oppure
   aggiungilo a mano: ⋮ → **Repository personalizzati** →
   `https://github.com/sandreialexandru/Smart-Heating-Control` come
   **Integrazione**. Senza HACS, copia `custom_components/advanced_climate` in
   `config/custom_components`.
2. **Aggiungi la casa**: **Impostazioni → Dispositivi e servizi → Aggiungi
   integrazione → Smart Heating Control**, oppure con questo pulsante:

   [![Apri il tuo Home Assistant e aggiungi Smart Heating Control](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=advanced_climate)

   Scegli le persone e il termostato che scalda la casa: per una casa con un
   solo termostato hai finito.
3. **Aggiungi le stanze** (facoltativo) con le loro valvole o i loro
   termostati, dalla pagina dell'integrazione, e metti la scheda su una
   dashboard.

Richiede Home Assistant **2026.6.0** o successivo.

**Non sai cosa scegliere?** Il
[configuratore interattivo](https://github.com/sandreialexandru/Smart-Heating-Control/blob/main/docs/configurator.html)
(in inglese o rumeno) parte da cosa scalda la tua casa e compila le risposte
adatte, passa per ogni modulo, spiega ogni scelta con cosa cambia e un
esempio, e finisce con un riepilogo di cosa impostare e dei problemi trovati
(come un dispositivo in due ruoli). Scarica il file e aprilo in un browser.

## Documentazione

La documentazione è in inglese e in rumeno.

| Documento | Cosa contiene |
|---|---|
| [Guida](docs/guide/README.md) | Passo per passo, in parole semplici: ogni impostazione, ogni tipo di riscaldamento, esempi |
| [Testato con](docs/tested-with.md) | I dispositivi confermati dagli utenti |
| [Come impara l'integrazione](docs/learning.md) | Il modello della stanza, con esempi svolti e simulazioni |
| [Riferimento](docs/reference.md) | Ogni regola, sensore, attributo, servizio e opzione della scheda, nel dettaglio tecnico |
| [Specifica](docs/SPEC.md) | La specifica completa |
| [Novità](CHANGELOG.md) | Cosa è cambiato, versione per versione |

## Traduzioni

Integrazione e scheda: inglese, rumeno, tedesco, olandese, francese e
italiano. Documentazione: inglese e rumeno.

I testi in italiano sono nuovi. Qualcosa suona strano o lo diresti in un
altro modo? Aiutaci in [questa issue](https://github.com/sandreialexandru/Smart-Heating-Control/issues/12).

## Supporto

Se Smart Heating Control ti è utile, puoi offrirmi un caffè su
[Ko-fi](https://ko-fi.com/sandreialexandru). Grazie!

## Licenza

MIT
