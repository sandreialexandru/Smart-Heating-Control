# 1. Concepts

*[Română](01-concepte.ro.md) · [Contents](README.md)*

## What the integration does, in short

Smart Heating Control decides **how warm every room should be** and tells the
heating devices (thermostats, radiator valves, relays) what to do. It takes
into account:

- the **schedule**: e.g. 21 °C during the day, 18 °C at night;
- **who is home**: when everybody leaves, the house cools down by itself, and
  when someone comes back it warms up again;
- **windows**: an open window turns the room's heating off or down;
- the **weather**: when it is warm outside, the heating stops;
- **what you do by hand**: if you change the temperature on a thermostat, the
  integration keeps the change for a while;
- **safety**: the house never freezes and never overheats.

The integration does not replace your thermostat. If you use **Generic
Thermostat** (the generic thermostat of Home Assistant), it keeps working
exactly as before; the integration only picks the right preset ("home",
"sleep", "away"…).

## The house and the rooms

The setup has two levels:

- **The house** is one entry of the integration. It holds what is shared: the
  people, the zones, the global mode (Auto / Vacation / Off / Summer), the
  weather, the boiler, the alerts.
- **Rooms** are added to the house. Every room has its own devices, sensors,
  windows and schedule.

When you create the house you also pick the **heating of the whole house**:
usually the thermostat that starts the boiler. It becomes the zone **Whole
house**, which behaves like a room. For a flat heated by one thermostat this
is all you need: you add no room.

Add separate rooms only when some rooms have their own valves or thermostats
(e.g. TRVs, thermostatic radiator valves).

**Example.** A flat with a gas boiler and one thermostat in the living room:
create the house, pick the thermostat under *Heating of the whole house*, done.
A house with TRVs in every room: create the house (you may pick *No heating
devices yet*), then add one room for every room with a TRV.

## The levels (presets)

Instead of working with temperatures directly, the integration works with
**levels**. Every level has a temperature, and some levels have a **fixed
role**:

| Level | Role | Default temperature (rooms without Generic Thermostat) |
| --- | --- | --- |
| `home` | someone is home, during the day | 21 °C |
| `sleep` | at night, with someone home | 18 °C |
| `eco` | nobody home, but someone is nearby (e.g. in town) | 17 °C |
| `away` | everybody is far, or vacation | 12 °C |
| `comfort` | no automatic role; you use it in the schedule | 22 °C |
| `activity` | no automatic role; you use it in the schedule | 20 °C |

The names come from the presets of Generic Thermostat. For a room with Generic
Thermostat the temperatures are those set in GT; the integration only picks the
preset. For the other rooms the temperatures are set in the integration, and
the level names can be changed (e.g. "Day" instead of `home`).

Besides the levels there are two limits:

- **frost protection** (7 °C by default, or the minimum temperature of
  Generic Thermostat): the lowest temperature a room ever gets;
- **maximum temperature** (25 °C by default): no target goes above it.

## The decision

For every room the integration always works out **one decision**: which rule
applies now and which target follows. The decision is shown by the room's
*Decision* sensor and in the card, with its reason. For example:

- *Schedule: home*;
- *Everyone is far (outside the nearby zones)*;
- *Window open: frost protection*.

The decision is worked out again **at once** when something important changes
(someone leaves, a window opens, the schedule time comes) and also
periodically (every 5 minutes by default), as a safety check.

## The order of the rules

So that two rules never contradict each other, they have a **fixed order**.
They are checked from top to bottom, and the first one that applies decides:

1. **Safety**: frost protection and maximum temperature. Always applied, even
   over a manual change or in a pause.
2. **Pause**: the integration sends only the safety.
3. **Valve exercise**: once a week the TRVs open fully for a few minutes,
   against limescale.
4. **Mode Off / Summer / outside the season**: heating off (with Off, only
   frost protection).
5. **Window open**.
6. **Manual change**.
7. **Vacation**: `away`.
8. **Presence**: far → `away`, nearby → `eco` (or a fixed temperature).
9. **Schedule**: with optimal start and stop and room occupancy.

After a rule decides, the **adjustments** apply (turning off when warm outside,
compensation for cold, tariff, PV, solar gain), and at the end the result goes
through the **safety limits** again.

**Example.** It is 10:00, the schedule says `home` (21 °C), everybody is away,
and a living room window is open. Rules 1–4 do not apply (no pause, mode
Auto). Rule 5, window open, applies: the living room goes to frost protection.
In the bedroom, with the window closed, rule 8 is reached: everybody is far,
so `away`.

A presence or vacation rule **never raises** the temperature above what is
"normal": e.g. on a day without an active profile in the schedule (frost
protection), leaving does not bring `away`, which would be warmer; frost
protection stays.

## Temperature unit

Every house has one unit, °C or °F. All temperatures of the house are entered
and shown in it. Thermostats and sensors may use another unit: the integration
converts. The unit is changed with *Reconfigure* on the integration page, and
the values are converted.

## Words used in the guide

| Word | Meaning |
| --- | --- |
| Generic Thermostat (GT) | The generic thermostat of Home Assistant: it switches a relay or a boiler from a temperature sensor |
| TRV | Thermostatic radiator valve, controlled over Zigbee, Z-Wave or Wi-Fi |
| Relay | A switch (`switch` or `input_boolean`) that turns the heating on directly |
| Heat source | The boiler or the relay that starts it |
| Hysteresis | How far the temperature may fall or rise around the target before a relay starts or stops; avoids frequent switching |
| Tolerance | How far below the target a thermostat lets the room fall before heating |
| `hvac_action` | What a thermostat reports: heating now or not |
| Reevaluation | Working out the decision again |
| Frost protection | The lowest, safety temperature |
| Optimal start | Heating starts earlier so the next level is reached exactly at the schedule time |
| Optimal stop | The colder level starts earlier, while the room stays comfortable until the schedule time |
