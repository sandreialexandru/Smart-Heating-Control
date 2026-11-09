# 11. Entități, servicii și automatizări

*[English](11-entities-and-services.md) · [Cuprins](README.ro.md)*

Numele entităților sunt date ca în interfața în română. ID-urile încep cu numele casei sau al camerei, de exemplu
`sensor.dormitor_decision`.

## Entitățile casei

| Entitate | Ce arată / face |
| --- | --- |
| *Mod* (select) | Modul: `auto`, `away`, `vacation`, `off`, `summer`. |
| *Prezență* (senzor) | `home`, `nearby`, `far`; atribute: persoanele, `arriving`, `guest_mode`, `vacation_active`, `vacation_suspended`, `vacation_preheating`, `pending`, `pending_since`. |
| *Pauză* (comutator) | Pauza. |
| *Mod oaspeți* (comutator) | Modul oaspeți (starea casei rămâne *acasă*). |
| *Început vacanță*, *Sfârșit vacanță* (dată și oră) | Perioada vacanței. Un sfârșit înainte de început (sau egal cu el) e refuzat, ca la `set_vacation`. |
| *Sezon de încălzire* (senzor binar) | Dacă e sezonul de încălzire. |
| *Cald afară* (senzor binar) | Dacă încălzirea e oprită pentru că e cald. |
| *Cerere de căldură* (senzor binar) | Dacă se cere acum căldură. |
| *Medie afară* (senzor) | Media de afară pe *Medie pe* ore; atribute: ultima valoare, motivul opririi (`cutoff_reason`: `measured`, `forecast_warm`, `forecast_cold`), media prognozei (`forecast_mean`), pragurile, prognoza, semnalul solar așteptat la fiecare 15 minute (`sun_forecast`, cu entitate meteo). |
| *Timp de încălzire* (senzor) | Ore totale de încălzire ale casei. |
| *Anulează modificările manuale* (buton) | Anulează modificările manuale din toate camerele. |
| *Șterge vacanța* (buton) | Anulează vacanța. |
| *Reevaluează* (buton) | Recalculează totul acum. |

## Entitățile unei camere

| Entitate | Ce arată / face |
| --- | --- |
| *Decizie* (senzor) | Regula care decide acum (mai jos), cu multe atribute. |
| *Temperatură țintă* (senzor) | Ținta, în unitatea casei. |
| *Temperatura camerei* (senzor) | Temperatura camerei folosită de integrare. |
| *Următoarea schimbare* (senzor) | Următoarea schimbare din program; atribute: nivelul următor, profilul. |
| *Viteză de încălzire* (senzor) | Minute pe grad cu încălzirea pornită, la temperatura camerei și cea de afară de acum; atribute: încălzirea învățată (`heating_per_hour`), curba de temperatură (`weather_curve`), câștigul solar învățat (`sun_gain`), pierderea de căldură (`loss_per_hour`), inerția (`inertia_minutes`), căldura care ajunge acum în cameră, minutele pe grad la −10 / 0 / 10 / 20 °C, progresul învățării (`hours_heating`, `hours_idle`, `hours_needed`) ([capitolul 7](07-anticipare-si-invatare.ro.md) și [Cum învață integrarea](../learning.ro.md#12-unde-se-vede)). |
| *Viteză de răcire* (senzor) | Cât de repede scade camera acum fără încălzire (gol până se învață). |
| *Timp de încălzire* (senzor) | Ore totale de încălzire ale camerei. |
| *Cerere de căldură* (senzor binar) | Dacă camera cere căldură; atributul `heating` arată dacă sursa ei merge. |
| *Fereastră deschisă* (senzor binar) | Dacă o fereastră contează acum ca deschisă. |
| *Modificare manuală* (senzor binar) | Dacă e activă o modificare manuală. |
| *Blocare modificări* (comutator) | Blocarea pentru copii. |
| *Anulează modificarea manuală* (buton) | Anulează modificarea manuală a camerei. |
| *Resetează învățarea* (buton) | Uită învățarea camerei; camera învață din nou în circa o zi. |
| *Profil de program* (select) | Profilul folosit azi; alegerea unuia îl pornește (vezi [capitolul 4](04-program.ro.md#selectul-de-profil)). Doar pentru camerele cu programul lor. |
| *Nivel Home* … *Nivel Activity*, *Temperatură „aproape”* (numere) | Temperaturile nivelurilor, doar la camerele fără Generic Thermostat. Un nivel cu nume propriu apare ca *Level „nume”*. |

### Stările senzorului *Decizie*

| Stare | Înseamnă |
| --- | --- |
| `starting` | Integrarea pornește încă |
| `frost_protection` | Antiîngheț |
| `maximum_temperature` | Temperatura maximă |
| `pause` | Pauză |
| `mode_off` | Modul Oprit |
| `summer` | Modul Vară |
| `out_of_season` | În afara sezonului de încălzire |
| `valve_exercise` | Mișcarea robinetelor |
| `window_open` | Fereastră deschisă |
| `manual_override` | Modificare manuală |
| `vacation` | Vacanță |
| `house_away` | Mod plecat |
| `presence_far` | Toți sunt departe |
| `presence_nearby` | Nimeni acasă, cineva aproape |
| `room_unoccupied` | Camera neocupată |
| `sensor_fallback` | Senzorii de temperatură indisponibili |
| `schedule` | Programul |
| `optimal_start` | Pornire anticipată |
| `optimal_stop` | Oprire anticipată |
| `outdoor_cutoff` | Cald afară |

### Atribute utile ale senzorului *Decizie*

| Atribut | Ce conține |
| --- | --- |
| `reason`, `reason_key`, `reason_params` | Motivul (text în engleză, și cheia cu parametrii pentru traducere) |
| `preset`, `target_temperature`, `current_temperature` | Nivelul, ținta, temperatura camerei |
| `offsets` | Ajustările active |
| `profile`, `next_change`, `next_preset`, `plan` | Profilul de azi, următoarea schimbare, planul următoarelor ore |
| `time_to_target` | Minutele până la țintă |
| `temperature_trend` | 1 cât camera se încălzește, −1 cât se răcește, 0 cât e stabilă sau nu se știe încă: cel puțin 0,2 °C pe oră în ultimele 30 de minute |
| `next_estimate` | Următoarea pornire / oprire anticipată: `kind`, `at`, `preset`, `minutes`, `starts_at`, `started_at`, `outdoor`, `outdoor_source`, `learned`, `sent_as`, `temperature` |
| `stop_forecast` | Temperatura estimată la schimbare, în timpul unei opriri anticipate |
| `humidity` | Cu senzor de umiditate: umiditatea camerei (%) |
| `surface_humidity` | Cu senzor de umiditate și temperatură de afară: umiditatea la peretele cel mai rece (%), pentru alerta de risc de mucegai ([capitolul 9](09-ferestre-manual-siguranta.ro.md)) |
| `optimal_stop_cancelled` | Dacă oprirea anticipată a fost anulată |
| `no_heat_reason` | De ce nu încălzește o cameră sub țintă |
| `override`, `hold_until` | Modificarea manuală activă și până când ține planul actual |
| `alerts` | Alertele camerei |
| `window_open`, `presence`, `heat_demand`, `heating` | Stările de acum |

## Servicii

Camera se alege cu `room` (nume sau id) sau cu `entity_id` (orice entitate a
camerei sau termostatul ei). Cu mai multe case, serviciile casei cer
`config_entry_id`.

### `advanced_climate.set_override`

Pune un nivel sau o temperatură ca modificare manuală.

| Câmp | Ce e |
| --- | --- |
| `room` / `entity_id` | Camera |
| `preset` | Nivelul (de exemplu `comfort`); spațiile din jur și literele mari nu contează |
| `temperature` | Temperatura, în unitatea casei |
| `duration_hours` | Orele, între 0,25 și 72 (ca în opțiunile casei); gol = regula configurată pentru modificări manuale |

Se dă fie `preset`, fie `temperature`. Temperatura e limitată între antiîngheț
și maxim. O temperatură care nu e număr (`nan`, `inf`) și o durată în afara
intervalului 0,25–72 ore (inclusiv 0 sau negativă) sunt refuzate cu o eroare.

```yaml
action: advanced_climate.set_override
data:
  room: Sufragerie
  temperature: 23
  duration_hours: 3
```

### `advanced_climate.clear_override`

Revine la automat (toate camerele, dacă nu se dă o cameră; o cameră care nu există dă o eroare).

### `advanced_climate.set_vacation`

Setează perioada vacanței; valori goale o anulează.

```yaml
action: advanced_climate.set_vacation
data:
  start: "2026-12-20 08:00:00"
  end: "2026-12-27 18:00:00"
```

Sfârșitul trebuie să fie după început.

### `advanced_climate.reevaluate`

Recalculează toate camerele acum.

### `advanced_climate.set_schedule`

Înlocuiește programul unei camere: `schedule` (textul) sau `profiles` (un
obiect: profil → listă de oră și nivel), opțional `profile_days` (zilele și
pornit / oprit ale fiecărui profil). Nu merge pentru camerele cu Schedule
helper (atunci se editează helperul). Un `profiles` greșit dă o eroare clară, de
exemplu *Profile "workday": every slot needs "time" and "preset"*.

Exemplu cu `profiles`:

```yaml
action: advanced_climate.set_schedule
data:
  room: Birou
  profiles:
    workday:
      - {time: "00:00", preset: sleep}
      - {time: "07:30", preset: home}
```

```yaml
action: advanced_climate.set_schedule
data:
  room: Birou
  schedule: |
    workday: 00:00 sleep, 07:30 home, 18:00 sleep
    weekend: 00:00 sleep
```

## Evenimentul `advanced_climate_decision_changed`

Apare de fiecare dată când o cameră își schimbă decizia, cu `room`,
`old_rule`, `rule`, `old_target`, `target`, `reason`.

**Exemplu de automatizare**: o notificare când o cameră trece pe fereastră
deschisă.

```yaml
triggers:
  - trigger: event
    event_type: advanced_climate_decision_changed
    event_data:
      rule: window_open
actions:
  - action: notify.mobile_app_telefon
    data:
      message: "Fereastră deschisă în {{ trigger.event.data.room }}"
```

## Alte exemple de automatizări

**Musafiri**: modul oaspeți pornit (se oprește singur după *Modul oaspeți se oprește după* ore, dacă e setată o valoare).

```yaml
actions:
  - action: switch.turn_on
    target:
      entity_id: switch.acasa_guest_mode
```

**Modul Vară la 1 mai** (dacă nu se folosește
sezonul între date sau automat):

```yaml
triggers:
  - trigger: template
    value_template: "{{ now().month == 5 and now().day == 1 }}"
actions:
  - action: select.select_option
    target:
      entity_id: select.acasa_mode
    data:
      option: summer
```

**Comfort la baie pentru duș**, pornit de un buton:

```yaml
actions:
  - action: advanced_climate.set_override
    data:
      room: Baie
      preset: comfort
      duration_hours: 1
```

**O cameră de obicei la 16 °C și la 22 °C cât e folosită.** Camera are un
program cu un singur start la 00:00 pe nivelul *Home*, pus la 16 °C în
*Niveluri*. Integrarea nu are o entitate climate proprie (comandă
termostatele existente, nu le înlocuiește): temperatura se schimbă cu
acțiunile ei. În editorul de automatizări: *Adaugă acțiune* → se caută
**Smart Heating Control**.

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.birou_ocupare
    to: "on"
    id: "intra"
  - trigger: state
    entity_id: binary_sensor.birou_ocupare
    to: "off"
    for: "00:15:00"
    id: "iese"
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: "intra"
        sequence:
          # 22 °C cel mult 4 ore (apoi revine singură la 16 °C)
          - action: advanced_climate.set_override
            data:
              room: Birou
              temperature: 22
              duration_hours: 4
      - conditions:
          - condition: trigger
            id: "iese"
        sequence:
          # Înapoi la program (16 °C)
          - action: advanced_climate.clear_override
            data:
              room: Birou
```

Un script cu aceeași acțiune e și el o entitate (`script.*`): se pune pe un
dashboard ca buton sau se pornește prin voce.

## Diagnosticul

Pe pagina integrării, **⋮ → Descarcă diagnosticul** dă configurația, învățarea
fiecărei camere (`thermal_model`: numerele învățate și cei zece candidați de
inerție cu erorile lor) și ultimele 100 de decizii ale
fiecărei camere. E util la
raportarea unei probleme. Datele personale sunt lăsate deoparte (apar ca
`**REDACTED**`): destinatarii alertelor, persoanele și unde sunt, zonele
apropiate, senzorii de distanță și de timp de drum și textul evenimentului din
calendar.
