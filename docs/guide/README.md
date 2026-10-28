# The complete Smart Heating Control guide

*[Română](README.ro.md)*

This guide explains **the whole integration**: what it does, how to set it up
step by step and how it decides. It is written also for people who are not
specialists and just want the heating to run by itself. Technical words are
explained the first time they appear, and every chapter has examples.

If you only want to get started, read chapters 1, 2 and 3. Read the rest when
you need a particular feature.

To set up step by step with an explanation for every choice, use the
[interactive configurator](../configurator.html) (download it and open it in a
browser).

## Contents

| Chapter | About |
| --- | --- |
| [1. Concepts](01-concepts.md) | What the integration does, the house and the rooms, the levels, the decision and the order of the rules |
| [2. Installation and the house](02-install-and-house.md) | Installing, creating the house, the heating of the whole house, every option of the house |
| [3. Rooms](03-rooms.md) | Adding a room for every kind of heating (Generic Thermostat, TRVs / other thermostats, relay), every step explained |
| [4. Schedule](04-schedule.md) | Profiles, days, calendar, workdays, start of the day, Schedule helper |
| [5. Presence and vacation](05-presence.md) | Home / nearby / far, zones, delays, presence sensors, guests, preheating on the way home, room occupancy, vacation |
| [6. Weather and season](06-weather.md) | Outdoor temperature, turning off when warm, the forecast, heating season, compensation, solar gain |
| [7. Optimal start and stop, learning](07-optimal-start-stop-and-learning.md) | How every room learns how long it takes to warm up and to cool down, and how it uses that |
| [8. Heat source and energy](08-heat-source-and-energy.md) | A boiler started by the integration, rooms needed, reference room, minimum times, tariff, PV, heating time |
| [9. Windows, manual changes and safety](09-windows-manual-safety.md) | Windows, manual changes, child lock, pause, modes, frost protection, maximum, command checks, alerts, valve exercise |
| [10. The card](10-card.md) | The Lovelace card: what it shows, how to use it, every option |
| [11. Entities, services and automations](11-entities-and-services.md) | Every entity, the services, the event, diagnostics, automation examples |
| [12. Examples and questions](12-examples-and-faq.md) | Complete setups for common homes, frequent questions, what to do when something does not work |

## Other documents

- [Specification](../SPEC.md): every rule and default value, in short tables.
- [How the integration learns](../learning.md): the maths of the learning, with full calculations and simulations.

## How to read the examples

Numbers in the examples are of two kinds, and the text always says which:

- **default values** of the integration (e.g. the frost protection of 7 °C):
  what you get if you change nothing;
- **values chosen for the example** (e.g. "a target of 21 °C"): only there to
  show the calculation; yours may differ.

When an example calculates something, the calculation is written out.

Setting names are given as in the English interface.
