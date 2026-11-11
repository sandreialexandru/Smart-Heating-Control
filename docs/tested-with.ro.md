# Smart Heating Control – testat cu

*[English](tested-with.md) · [README](../README.ro.md) · [Ghid](guide/README.ro.md)*

Smart Heating Control lucrează cu orice entitate `climate`, `switch` sau
`sensor` de temperatură din Home Assistant, indiferent de marcă. Acestea sunt
dispozitivele confirmate până acum de utilizatori:

| Dispozitiv | Folosit ca |
| --- | --- |
| Sonoff TRVZB (Zigbee2MQTT) | TRV-uri comandate prin temperatură, cu calibrare *Offset* sau *Temperatură externă* după un senzor de cameră (*Temperatură externă* cere `temperature_sensor_select` pus pe extern în Zigbee2MQTT) |
| TRV-uri Zigbee (mai multe pe cameră) | TRV-uri comandate prin temperatură |
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
