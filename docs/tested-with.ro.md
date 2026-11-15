# Smart Heating Control – testat cu

*[English](tested-with.md) · [README](../README.ro.md) · [Ghid](guide/README.ro.md)*

Smart Heating Control lucrează cu orice entitate `climate`, `switch` sau
`sensor` de temperatură din Home Assistant, indiferent de marcă. Acestea sunt
dispozitivele confirmate până acum de utilizatori:

| Dispozitiv | Folosit ca |
| --- | --- |
| Sonoff TRVZB (Zigbee2MQTT) | TRV-uri comandate prin temperatură, cu calibrare *Offset* sau *Temperatură externă* după un senzor de cameră (*Temperatură externă* cere `temperature_sensor_select` pus pe extern în Zigbee2MQTT) |
| TRV-uri Zigbee (mai multe pe cameră) | TRV-uri comandate prin temperatură |
| Tuya TRV602Z (Zigbee2MQTT) | TRV-uri comandate prin temperatură. Modul nu se poate schimba din Home Assistant, așa că rămâne pe *auto* (2.6.5 sau mai nou); nu folosi presetul `on` (valva 100 %). *Lock*-ul camerei păstrează valoarea SHC dacă programul propriu al TRV-ului o schimbă |
| EARU TRV06, AVATTO ME167, AVATTO TRV26 (Zigbee2MQTT) | TRV-uri comandate prin temperatură |
| Sonoff MINI-ZBD (Zigbee2MQTT) | Releu |
| HOBEIAN ZG-227Z (Zigbee2MQTT) | Senzorul camerei |
| Termostat Hive (local, Zigbee) | Sursă de căldură care pornește centrala |
| Releu Shelly | Sursă de căldură (releul centralei) |
| Contact uscat Tuya Zigbee (TS0001) | Sursă de căldură, printr-un template switch (apare ca `light`) |
| Generic Thermostat | Încălzirea întregii case sau a unei camere |
| Releu ESP32 (ESPHome) | Comutatorul unui Generic Thermostat care pornește centrala |
| Senzori de temperatură Sonoff Zigbee (cu și fără display) | Senzorii camerelor |
| Senzor de temperatură Xiaomi | Senzorul camerei (și pentru calibrarea TRV-ului) |

Integrarea merge și cu alt dispozitiv? Se poate spune într-un
[issue](https://github.com/sandreialexandru/Smart-Heating-Control/issues), ca
dispozitivul să fie adăugat aici.
