# Smart Heating Control – tested with

*[Română](tested-with.ro.md) · [README](../README.md) · [Guide](guide/README.md)*

Smart Heating Control works with any `climate`, `switch` or temperature
`sensor` entity of Home Assistant, whatever the brand. These are the devices
users have confirmed so far:

| Device | Used as |
| --- | --- |
| Sonoff TRVZB (Zigbee2MQTT) | TRVs commanded by temperature, with *Offset* or *External temperature* calibration from a room sensor (*External temperature* needs `temperature_sensor_select` set to external in Zigbee2MQTT) |
| Zigbee TRVs (several per room) | TRVs commanded by temperature |
| Hive thermostat (local, Zigbee) | Heat source that starts the boiler |
| Shelly relay | Heat source (the boiler relay) |
| Tuya Zigbee dry contact (TS0001) | Heat source, through a template switch (it shows up as a `light`) |
| Generic Thermostat | Heating of the whole house, or a room |
| ESP32 relay (ESPHome) | The switch of a Generic Thermostat that starts the boiler |
| Sonoff Zigbee temperature sensors (with and without display) | Room sensors |
| Xiaomi temperature sensor | Room sensor (also for the TRV calibration) |

Using it with another device? Tell us in an
[issue](https://github.com/sandreialexandru/Smart-Heating-Control/issues), so
it can be added here.
