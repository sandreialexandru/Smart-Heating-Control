"""Alert texts, categories and delivery rules for the notifications.

The card shows the alerts in its own language from their code and values; the
notifications use the same texts here, in the language of Home Assistant.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

# How much an alert matters: important ones are sent at once (also in the quiet
# hours), warnings are held until the quiet hours end, information too.
CATEGORY_CRITICAL = "critical"
CATEGORY_WARNING = "warning"
CATEGORY_INFO = "info"

CATEGORIES: dict[str, str] = {
    # No heating at all, or a room that cannot heat.
    "source_unavailable": CATEGORY_CRITICAL,
    "circuit_unavailable": CATEGORY_CRITICAL,
    "device_unavailable": CATEGORY_CRITICAL,
    # The other heat source heats meanwhile.
    "source_unavailable_other": CATEGORY_WARNING,
    # Something to look at.
    "sensor_unavailable": CATEGORY_WARNING,
    "sensor_silent": CATEGORY_WARNING,
    "no_effect": CATEGORY_WARNING,
    "outdoor_unavailable": CATEGORY_WARNING,
    "window_long": CATEGORY_WARNING,
    "battery_low": CATEGORY_WARNING,
    "not_accepted": CATEGORY_WARNING,
    "room_difference": CATEGORY_WARNING,
    "device_limit_max": CATEGORY_WARNING,
    "device_limit_min": CATEGORY_WARNING,
    "preset_missing": CATEGORY_WARNING,
    "schedule_invalid": CATEGORY_WARNING,
    "schedule_gap": CATEGORY_WARNING,
    "weather_without_source": CATEGORY_WARNING,
    "boiler_min_rooms": CATEGORY_WARNING,
    "frost_protection": CATEGORY_WARNING,
    "pause_long": CATEGORY_WARNING,
    "mold_risk": CATEGORY_WARNING,
    # What the house did by itself.
    "auto_vacation_on": CATEGORY_INFO,
    "auto_vacation_off": CATEGORY_INFO,
    "season_on": CATEGORY_INFO,
    "season_off": CATEGORY_INFO,
    "guest_ended": CATEGORY_INFO,
    "vacation_started": CATEGORY_INFO,
    "vacation_preheat": CATEGORY_INFO,
}

# Alerts whose end is worth telling (a device back, a window closed); the others
# end because a setting changed, and no one waits for that.
RESOLVABLE = {
    "source_unavailable",
    "source_unavailable_other",
    "circuit_unavailable",
    "device_unavailable",
    "sensor_unavailable",
    "sensor_silent",
    "no_effect",
    "outdoor_unavailable",
    "window_long",
    "battery_low",
    "not_accepted",
    "frost_protection",
    "mold_risk",
}

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "source_unavailable": "The heat source {entity} has been unavailable for more than {minutes} min: no heating, not even frost protection.",
        "source_unavailable_other": "The heat source {entity} has been unavailable for more than {minutes} min: {other} heats meanwhile.",
        "circuit_unavailable": "The circuit relay {entity} has been unavailable for more than {minutes} min: the rooms of its circuit get no heat. Repair the relay or change the circuits of the house.",
        "room_difference": "Some rooms stay cold while others are warm: {rooms}.",
        "preset_missing": "The level {level} is not available on {entity} and its temperature is unknown.",
        "not_accepted": "{entities} did not accept {target}.",
        "window_long": "A window has been open for more than {minutes} min.",
        "device_unavailable": "{entity} has been unavailable for more than {minutes} min.",
        "sensor_unavailable_device": "The temperature sensors are unavailable; the device sensor is used.",
        "sensor_unavailable_eco": "The temperature sensors are unavailable; eco is used.",
        "sensor_silent": "{entity} has sent no temperature for more than {hours} h; the room is controlled by an old value. Check its battery and its signal.",
        "sensor_silent_left_out": "{entity} has sent no temperature for more than {hours} h; it is left out until it reports again. Check its battery and its signal.",
        "no_effect": "Heating for {hours} h, but the temperature rose by only {rise}° (about {expected}° expected). Check the valve, the heat source and the windows.",
        "schedule_invalid": "The schedule is invalid ({error}); the default schedule is used.",
        "schedule_gap": "No active schedule profile: {days}; the room keeps its frost protection on those days.",
        "battery_low": "Low battery on {device} ({level}%).",
        "device_limit_max": "{entity} accepts at most {value}: raise its Max temperature on the device if the room needs more.",
        "device_limit_min": "{entity} accepts at least {value}: lower its Min temperature on the device for a lower frost protection.",
        "weather_without_source": "On but not working without an outdoor temperature sensor or a weather entity: {features}.",
        "boiler_min_rooms": "Rooms needed to start the heat source is {needed}, but the house has {rooms} rooms that can start it: the heat source starts only for frost protection.",
        "outdoor_unavailable": "No outdoor temperature from {entities} for more than {minutes} min: the cutoff, the automatic season, the compensation and the optimal stop cannot use it.",
        "auto_vacation_on": "Everyone has been away for a long time: the automatic vacation started.",
        "auto_vacation_off": "The automatic vacation ended.",
        "frost_protection": "The room is {current}°, below the frost protection temperature ({frost}°): the heating cannot keep it.",
        "mold_risk": "Mold risk: the coldest wall reached about {surface}% humidity (room {humidity}%). Airing the room and keeping it warmer lower the risk.",
        "pause_long": "The heating has been paused for more than {hours} h: only frost protection works.",
        "season_on": "The heating season started.",
        "season_off": "The heating season ended: no heating until it starts again.",
        "guest_ended": "Guest mode ended by itself: the house follows the people again.",
        "vacation_started": "The vacation started: every room is set to away.",
        "vacation_preheat": "The vacation ends soon: the house is warmed up for your return.",
        # Resolved.
        "resolved_source_unavailable": "The heat source {entity} works again.",
        "resolved_source_unavailable_other": "The heat source {entity} works again.",
        "resolved_circuit_unavailable": "The circuit relay {entity} works again.",
        "resolved_device_unavailable": "{entity} is available again.",
        "resolved_sensor_unavailable": "The temperature sensors work again.",
        "resolved_sensor_silent": "{entity} sends the temperature again.",
        "resolved_no_effect": "The room warms up again.",
        "resolved_outdoor_unavailable": "The outdoor temperature is available again.",
        "resolved_window_long": "The window is closed again.",
        "resolved_battery_low": "The battery of {device} is fine again.",
        "resolved_not_accepted": "{entities} follow the target again.",
        "resolved_frost_protection": "The room is back at the frost protection temperature.",
        "resolved_mold_risk": "The mold risk is over: the walls are dry enough again.",
        # Values.
        "free_days": "free days (holidays)",
        "weekend_workdays": "workdays on the weekend",
        "wf_cutoff": "turn heating off when warm",
        "wf_season_auto": "automatic season",
        "wf_compensation": "outdoor compensation",
        "wf_window_ignore": "ignore windows above",
        "wf_forecast": "use the forecast (needs a weather entity and the cutoff)",
    },
    "ro": {
        "source_unavailable": "Sursa de căldură {entity} e indisponibilă de peste {minutes} min: nu se încălzește, nici pentru antiîngheț.",
        "source_unavailable_other": "Sursa de căldură {entity} e indisponibilă de peste {minutes} min: între timp încălzește {other}.",
        "circuit_unavailable": "Releul de circuit {entity} e indisponibil de peste {minutes} min: camerele circuitului lui nu primesc căldură. Trebuie reparat releul sau schimbate circuitele casei.",
        "room_difference": "Unele camere rămân reci, altele sunt calde: {rooms}.",
        "preset_missing": "Nivelul {level} nu există pe {entity} și temperatura lui e necunoscută.",
        "not_accepted": "{entities} nu a acceptat {target}.",
        "window_long": "O fereastră e deschisă de peste {minutes} min.",
        "device_unavailable": "{entity} e indisponibil de peste {minutes} min.",
        "sensor_unavailable_device": "Senzorii de temperatură sunt indisponibili; se folosește senzorul dispozitivului.",
        "sensor_unavailable_eco": "Senzorii de temperatură sunt indisponibili; se folosește eco.",
        "sensor_silent": "{entity} nu a mai trimis temperatura de peste {hours} h; camera e controlată după o valoare veche. Verifică bateria și semnalul.",
        "sensor_silent_left_out": "{entity} nu a mai trimis temperatura de peste {hours} h; e lăsat deoparte până trimite din nou. Verifică bateria și semnalul.",
        "no_effect": "Încălzește de {hours} h, dar temperatura a crescut doar cu {rise}° (așteptat aproximativ {expected}°). Verifică ventilul, sursa de căldură și ferestrele.",
        "schedule_invalid": "Programul e invalid ({error}); se folosește programul implicit.",
        "schedule_gap": "Fără profil activ în program: {days}; în acele zile camera rămâne pe antiîngheț.",
        "battery_low": "Baterie descărcată la {device} ({level}%).",
        "device_limit_max": "{entity} acceptă cel mult {value}: ridică Max temperature pe dispozitiv dacă e nevoie de mai mult.",
        "device_limit_min": "{entity} acceptă cel puțin {value}: coboară Min temperature pe dispozitiv pentru un antiîngheț mai jos.",
        "weather_without_source": "Pornite, dar nu funcționează fără senzor de temperatură exterioară sau entitate meteo: {features}.",
        "boiler_min_rooms": "Camere necesare pentru pornirea sursei de căldură: {needed}, dar casa are {rooms} camere care o pot porni: sursa de căldură pornește doar pentru antiîngheț.",
        "outdoor_unavailable": "Nicio temperatură de afară de la {entities} de peste {minutes} min: oprirea când e cald, sezonul automat, compensarea și oprirea anticipată nu o pot folosi.",
        "auto_vacation_on": "Toată lumea e plecată de mult: a pornit vacanța automată.",
        "auto_vacation_off": "Vacanța automată s-a încheiat.",
        "frost_protection": "Camera are {current}°, sub temperatura de antiîngheț ({frost}°): încălzirea nu o poate menține.",
        "mold_risk": "Risc de mucegai: umiditatea la peretele cel mai rece a ajuns la aproximativ {surface}% (camera {humidity}%). Aerisirea și o cameră mai caldă scad riscul.",
        "pause_long": "Încălzirea e în pauză de peste {hours} h: funcționează doar antiînghețul.",
        "season_on": "A început sezonul de încălzire.",
        "season_off": "S-a încheiat sezonul de încălzire: nu se mai încălzește până nu reîncepe.",
        "guest_ended": "Modul oaspeți s-a oprit singur: casa urmează din nou persoanele.",
        "vacation_started": "A început vacanța: toate camerele sunt pe away.",
        "vacation_preheat": "Vacanța se termină curând: casa se încălzește pentru întoarcerea voastră.",
        "resolved_source_unavailable": "Sursa de căldură {entity} funcționează din nou.",
        "resolved_source_unavailable_other": "Sursa de căldură {entity} funcționează din nou.",
        "resolved_circuit_unavailable": "Releul de circuit {entity} funcționează din nou.",
        "resolved_device_unavailable": "{entity} e din nou disponibil.",
        "resolved_sensor_unavailable": "Senzorii de temperatură funcționează din nou.",
        "resolved_sensor_silent": "{entity} trimite din nou temperatura.",
        "resolved_no_effect": "Camera se încălzește din nou.",
        "resolved_outdoor_unavailable": "Temperatura de afară e din nou disponibilă.",
        "resolved_window_long": "Fereastra e închisă din nou.",
        "resolved_battery_low": "Bateria de la {device} e din nou în regulă.",
        "resolved_not_accepted": "{entities} urmează din nou ținta.",
        "resolved_frost_protection": "Camera a revenit la temperatura de antiîngheț.",
        "resolved_mold_risk": "Riscul de mucegai a trecut: pereții sunt din nou destul de uscați.",
        "free_days": "zilele libere (sărbători)",
        "weekend_workdays": "zilele lucrătoare din weekend",
        "wf_cutoff": "oprirea când e cald",
        "wf_season_auto": "sezonul automat",
        "wf_compensation": "compensarea exterioară",
        "wf_window_ignore": "ignorarea ferestrelor peste",
        "wf_forecast": "prognoza (cere o entitate meteo și oprirea când e cald)",
    },
    "de": {
        "source_unavailable": "Die Wärmequelle {entity} ist seit mehr als {minutes} min nicht verfügbar: keine Heizung, nicht einmal Frostschutz.",
        "source_unavailable_other": "Die Wärmequelle {entity} ist seit mehr als {minutes} min nicht verfügbar: In der Zwischenzeit heizt {other}.",
        "circuit_unavailable": "Das Kreisrelais {entity} ist seit mehr als {minutes} min nicht verfügbar: Die Räume seines Kreises bekommen keine Wärme. Repariere das Relais oder ändere die Kreise des Hauses.",
        "room_difference": "Einige Räume bleiben kalt, während andere warm sind: {rooms}.",
        "preset_missing": "Die Stufe {level} gibt es auf {entity} nicht, und ihre Temperatur ist unbekannt.",
        "not_accepted": "{entities} hat {target} nicht übernommen.",
        "window_long": "Ein Fenster ist seit mehr als {minutes} min offen.",
        "device_unavailable": "{entity} ist seit mehr als {minutes} min nicht verfügbar.",
        "sensor_unavailable_device": "Die Temperatursensoren sind nicht verfügbar; der Sensor des Geräts wird genutzt.",
        "sensor_unavailable_eco": "Die Temperatursensoren sind nicht verfügbar; eco wird genutzt.",
        "sensor_silent": "{entity} hat seit mehr als {hours} h keine Temperatur gesendet; der Raum wird nach einem alten Wert geregelt. Prüfe Batterie und Empfang.",
        "sensor_silent_left_out": "{entity} hat seit mehr als {hours} h keine Temperatur gesendet; er bleibt außen vor, bis er wieder meldet. Prüfe Batterie und Empfang.",
        "no_effect": "Seit {hours} h wird geheizt, aber die Temperatur ist nur um {rise}° gestiegen (erwartet etwa {expected}°). Prüfe das Ventil, die Wärmequelle und die Fenster.",
        "schedule_invalid": "Der Zeitplan ist ungültig ({error}); der Standard-Zeitplan wird genutzt.",
        "schedule_gap": "Kein aktives Zeitplan-Profil: {days}; der Raum bleibt an diesen Tagen auf Frostschutz.",
        "battery_low": "Batterie schwach bei {device} ({level} %).",
        "device_limit_max": "{entity} nimmt höchstens {value} an: Erhöhe am Gerät seine Max-Temperatur, wenn der Raum mehr braucht.",
        "device_limit_min": "{entity} nimmt mindestens {value} an: Senke am Gerät seine Min-Temperatur für einen niedrigeren Frostschutz.",
        "weather_without_source": "Eingeschaltet, aber ohne Außentemperatursensor oder Wetter-Entität wirkungslos: {features}.",
        "boiler_min_rooms": "Zum Starten der Wärmequelle sind {needed} Räume nötig, aber das Haus hat nur {rooms} Räume, die sie starten können: Die Wärmequelle startet nur für den Frostschutz.",
        "outdoor_unavailable": "Seit mehr als {minutes} min keine Außentemperatur von {entities}: Abschaltung, automatische Heizperiode, Kompensation und optimaler Stopp können sie nicht nutzen.",
        "auto_vacation_on": "Alle sind schon lange weg: Der automatische Urlaub hat begonnen.",
        "auto_vacation_off": "Der automatische Urlaub ist zu Ende.",
        "frost_protection": "Der Raum hat {current}°, weniger als die Frostschutztemperatur ({frost}°): Die Heizung schafft es nicht, ihn zu halten.",
        "mold_risk": "Schimmelgefahr: An der kältesten Wand wurden etwa {surface} % Feuchtigkeit erreicht (Raum {humidity} %). Lüften und etwas wärmer heizen senken das Risiko.",
        "pause_long": "Die Heizung ist seit mehr als {hours} h pausiert: Nur der Frostschutz arbeitet.",
        "season_on": "Die Heizperiode hat begonnen.",
        "season_off": "Die Heizperiode ist zu Ende: keine Heizung, bis sie wieder beginnt.",
        "guest_ended": "Der Gastmodus hat sich selbst beendet: Das Haus richtet sich wieder nach den Personen.",
        "vacation_started": "Der Urlaub hat begonnen: Alle Räume sind auf away.",
        "vacation_preheat": "Der Urlaub endet bald: Das Haus wird für eure Rückkehr vorgeheizt.",
        "resolved_source_unavailable": "Die Wärmequelle {entity} funktioniert wieder.",
        "resolved_source_unavailable_other": "Die Wärmequelle {entity} funktioniert wieder.",
        "resolved_circuit_unavailable": "Das Kreisrelais {entity} funktioniert wieder.",
        "resolved_device_unavailable": "{entity} ist wieder verfügbar.",
        "resolved_sensor_unavailable": "Die Temperatursensoren funktionieren wieder.",
        "resolved_sensor_silent": "{entity} sendet wieder die Temperatur.",
        "resolved_no_effect": "Der Raum wird wieder warm.",
        "resolved_outdoor_unavailable": "Die Außentemperatur ist wieder verfügbar.",
        "resolved_window_long": "Das Fenster ist wieder zu.",
        "resolved_battery_low": "Die Batterie von {device} ist wieder in Ordnung.",
        "resolved_not_accepted": "{entities} folgt wieder der Zieltemperatur.",
        "resolved_frost_protection": "Der Raum ist wieder auf Frostschutztemperatur.",
        "resolved_mold_risk": "Die Schimmelgefahr ist vorbei: Die Wände sind wieder trocken genug.",
        "free_days": "freie Tage (Feiertage)",
        "weekend_workdays": "Arbeitstage am Wochenende",
        "wf_cutoff": "Heizung aus, wenn es warm ist",
        "wf_season_auto": "automatische Heizperiode",
        "wf_compensation": "Außenkompensation",
        "wf_window_ignore": "Fenster ignorieren ab",
        "wf_forecast": "Vorhersage nutzen (braucht eine Wetter-Entität und die Abschaltung)",
    },
    "nl": {
        "source_unavailable": "De warmtebron {entity} is al meer dan {minutes} min onbeschikbaar: geen verwarming, zelfs geen vorstbeveiliging.",
        "source_unavailable_other": "De warmtebron {entity} is al meer dan {minutes} min onbeschikbaar: intussen verwarmt {other}.",
        "circuit_unavailable": "Het circuitrelais {entity} is al meer dan {minutes} min onbeschikbaar: de kamers van zijn circuit krijgen geen warmte. Repareer het relais of pas de circuits van het huis aan.",
        "room_difference": "Sommige kamers blijven koud terwijl andere warm zijn: {rooms}.",
        "preset_missing": "Het niveau {level} bestaat niet op {entity} en de temperatuur ervan is onbekend.",
        "not_accepted": "{entities} heeft {target} niet overgenomen.",
        "window_long": "Er staat al meer dan {minutes} min een raam open.",
        "device_unavailable": "{entity} is al meer dan {minutes} min onbeschikbaar.",
        "sensor_unavailable_device": "De temperatuursensoren zijn onbeschikbaar; de sensor van het apparaat wordt gebruikt.",
        "sensor_unavailable_eco": "De temperatuursensoren zijn onbeschikbaar; eco wordt gebruikt.",
        "sensor_silent": "{entity} heeft al meer dan {hours} u geen temperatuur gestuurd; de kamer wordt op een oude waarde geregeld. Controleer de batterij en het signaal.",
        "sensor_silent_left_out": "{entity} heeft al meer dan {hours} u geen temperatuur gestuurd; hij wordt genegeerd tot hij weer meldt. Controleer de batterij en het signaal.",
        "no_effect": "Al {hours} u aan het verwarmen, maar de temperatuur steeg maar {rise}° (ongeveer {expected}° verwacht). Controleer de kraan, de warmtebron en de ramen.",
        "schedule_invalid": "Het schema is ongeldig ({error}); het standaardschema wordt gebruikt.",
        "schedule_gap": "Geen actief schemaprofiel: {days}; de kamer blijft op die dagen op vorstbeveiliging.",
        "battery_low": "Batterij bijna leeg bij {device} ({level}%).",
        "device_limit_max": "{entity} accepteert hoogstens {value}: verhoog de maximumtemperatuur op het apparaat als de kamer meer nodig heeft.",
        "device_limit_min": "{entity} accepteert minstens {value}: verlaag de minimumtemperatuur op het apparaat voor een lagere vorstbeveiliging.",
        "weather_without_source": "Aan, maar werkt niet zonder buitentemperatuursensor of weerentiteit: {features}.",
        "boiler_min_rooms": "Er zijn {needed} kamers nodig om de warmtebron te starten, maar het huis heeft {rooms} kamers die hem kunnen starten: de warmtebron start alleen voor vorstbeveiliging.",
        "outdoor_unavailable": "Al meer dan {minutes} min geen buitentemperatuur van {entities}: de afschakeling, het automatische seizoen, de compensatie en de optimale stop kunnen hem niet gebruiken.",
        "auto_vacation_on": "Iedereen is al lang weg: de automatische vakantie is begonnen.",
        "auto_vacation_off": "De automatische vakantie is voorbij.",
        "frost_protection": "De kamer is {current}°, onder de vorstbeveiligingstemperatuur ({frost}°): de verwarming kan haar niet op temperatuur houden.",
        "mold_risk": "Schimmelrisico: de koudste muur bereikte ongeveer {surface}% vochtigheid (kamer {humidity}%). Luchten en de kamer iets warmer houden verlagen het risico.",
        "pause_long": "De verwarming staat al meer dan {hours} u op pauze: alleen de vorstbeveiliging werkt.",
        "season_on": "Het stookseizoen is begonnen.",
        "season_off": "Het stookseizoen is voorbij: geen verwarming tot het weer begint.",
        "guest_ended": "De gastmodus is vanzelf gestopt: het huis volgt weer de personen.",
        "vacation_started": "De vakantie is begonnen: alle kamers staan op away.",
        "vacation_preheat": "De vakantie is bijna voorbij: het huis warmt op voor jullie terugkomst.",
        "resolved_source_unavailable": "De warmtebron {entity} werkt weer.",
        "resolved_source_unavailable_other": "De warmtebron {entity} werkt weer.",
        "resolved_circuit_unavailable": "Het circuitrelais {entity} werkt weer.",
        "resolved_device_unavailable": "{entity} is weer beschikbaar.",
        "resolved_sensor_unavailable": "De temperatuursensoren werken weer.",
        "resolved_sensor_silent": "{entity} stuurt weer de temperatuur.",
        "resolved_no_effect": "De kamer warmt weer op.",
        "resolved_outdoor_unavailable": "De buitentemperatuur is weer beschikbaar.",
        "resolved_window_long": "Het raam is weer dicht.",
        "resolved_battery_low": "De batterij van {device} is weer in orde.",
        "resolved_not_accepted": "{entities} volgt de doeltemperatuur weer.",
        "resolved_frost_protection": "De kamer is weer op de vorstbeveiligingstemperatuur.",
        "resolved_mold_risk": "Het schimmelrisico is voorbij: de muren zijn weer droog genoeg.",
        "free_days": "vrije dagen (feestdagen)",
        "weekend_workdays": "werkdagen in het weekend",
        "wf_cutoff": "verwarming uit als het warm is",
        "wf_season_auto": "automatisch seizoen",
        "wf_compensation": "buitencompensatie",
        "wf_window_ignore": "ramen negeren boven",
        "wf_forecast": "de voorspelling gebruiken (heeft een weerentiteit en de afschakeling nodig)",
    },
    "fr": {
        "source_unavailable": "La source de chaleur {entity} est indisponible depuis plus de {minutes} min : plus de chauffage, même pas le hors-gel.",
        "source_unavailable_other": "La source de chaleur {entity} est indisponible depuis plus de {minutes} min : {other} chauffe en attendant.",
        "circuit_unavailable": "Le relais de circuit {entity} est indisponible depuis plus de {minutes} min : les pièces de son circuit ne reçoivent pas de chaleur. Réparez le relais ou modifiez les circuits de la maison.",
        "room_difference": "Certaines pièces restent froides alors que d'autres sont chaudes : {rooms}.",
        "preset_missing": "Le niveau {level} n'existe pas sur {entity} et sa température est inconnue.",
        "not_accepted": "{entities} n'a pas accepté {target}.",
        "window_long": "Une fenêtre est ouverte depuis plus de {minutes} min.",
        "device_unavailable": "{entity} est indisponible depuis plus de {minutes} min.",
        "sensor_unavailable_device": "Les capteurs de température sont indisponibles ; le capteur de l'appareil est utilisé.",
        "sensor_unavailable_eco": "Les capteurs de température sont indisponibles ; eco est utilisé.",
        "sensor_silent": "{entity} n'a envoyé aucune température depuis plus de {hours} h ; la pièce est régulée sur une ancienne valeur. Vérifiez sa pile et son signal.",
        "sensor_silent_left_out": "{entity} n'a envoyé aucune température depuis plus de {hours} h ; il est écarté jusqu'à ce qu'il se manifeste. Vérifiez sa pile et son signal.",
        "no_effect": "Chauffe depuis {hours} h, mais la température n'a monté que de {rise}° (environ {expected}° attendus). Vérifiez la vanne, la source de chaleur et les fenêtres.",
        "schedule_invalid": "Le planning est invalide ({error}) ; le planning par défaut est utilisé.",
        "schedule_gap": "Aucun profil de planning actif : {days} ; la pièce reste en hors-gel ces jours-là.",
        "battery_low": "Batterie faible sur {device} ({level} %).",
        "device_limit_max": "{entity} accepte au maximum {value} : augmentez sa température max sur l'appareil si la pièce a besoin de plus.",
        "device_limit_min": "{entity} accepte au minimum {value} : baissez sa température min sur l'appareil pour un hors-gel plus bas.",
        "weather_without_source": "Activé mais sans effet sans capteur de température extérieure ni entité météo : {features}.",
        "boiler_min_rooms": "Il faut {needed} pièces pour démarrer la source de chaleur, mais la maison n'a que {rooms} pièces capables de la démarrer : la source ne démarre que pour le hors-gel.",
        "outdoor_unavailable": "Aucune température extérieure de {entities} depuis plus de {minutes} min : la coupure, la saison automatique, la compensation et l'arrêt optimal ne peuvent pas l'utiliser.",
        "auto_vacation_on": "Tout le monde est absent depuis longtemps : les vacances automatiques ont commencé.",
        "auto_vacation_off": "Les vacances automatiques sont terminées.",
        "frost_protection": "La pièce est à {current}°, sous la température hors-gel ({frost}°) : le chauffage n'arrive pas à la maintenir.",
        "mold_risk": "Risque de moisissure : le mur le plus froid a atteint environ {surface} % d'humidité (pièce {humidity} %). Aérer et garder la pièce un peu plus chaude réduisent le risque.",
        "pause_long": "Le chauffage est en pause depuis plus de {hours} h : seul le hors-gel fonctionne.",
        "season_on": "La saison de chauffe a commencé.",
        "season_off": "La saison de chauffe est terminée : pas de chauffage jusqu'à ce qu'elle reprenne.",
        "guest_ended": "Le mode invité s'est arrêté tout seul : la maison suit de nouveau les personnes.",
        "vacation_started": "Les vacances ont commencé : toutes les pièces sont en away.",
        "vacation_preheat": "Les vacances se terminent bientôt : la maison se réchauffe pour votre retour.",
        "resolved_source_unavailable": "La source de chaleur {entity} fonctionne de nouveau.",
        "resolved_source_unavailable_other": "La source de chaleur {entity} fonctionne de nouveau.",
        "resolved_circuit_unavailable": "Le relais de circuit {entity} fonctionne de nouveau.",
        "resolved_device_unavailable": "{entity} est de nouveau disponible.",
        "resolved_sensor_unavailable": "Les capteurs de température fonctionnent de nouveau.",
        "resolved_sensor_silent": "{entity} envoie de nouveau la température.",
        "resolved_no_effect": "La pièce se réchauffe de nouveau.",
        "resolved_outdoor_unavailable": "La température extérieure est de nouveau disponible.",
        "resolved_window_long": "La fenêtre est refermée.",
        "resolved_battery_low": "La batterie de {device} est de nouveau correcte.",
        "resolved_not_accepted": "{entities} suit de nouveau la consigne.",
        "resolved_frost_protection": "La pièce est revenue à la température hors-gel.",
        "resolved_mold_risk": "Le risque de moisissure est passé : les murs sont de nouveau assez secs.",
        "free_days": "jours libres (fériés)",
        "weekend_workdays": "jours ouvrés le week-end",
        "wf_cutoff": "couper le chauffage quand il fait doux",
        "wf_season_auto": "saison automatique",
        "wf_compensation": "compensation extérieure",
        "wf_window_ignore": "ignorer les fenêtres au-dessus de",
        "wf_forecast": "utiliser les prévisions (nécessite une entité météo et la coupure)",
    },
    "it": {
        "source_unavailable": "La fonte di calore {entity} non è disponibile da più di {minutes} min: niente riscaldamento, nemmeno l'antigelo.",
        "source_unavailable_other": "La fonte di calore {entity} non è disponibile da più di {minutes} min: nel frattempo scalda {other}.",
        "circuit_unavailable": "Il relè di circuito {entity} non è disponibile da più di {minutes} min: le stanze del suo circuito non ricevono calore. Ripara il relè o cambia i circuiti della casa.",
        "room_difference": "Alcune stanze restano fredde mentre altre sono calde: {rooms}.",
        "preset_missing": "Il livello {level} non esiste su {entity} e la sua temperatura è sconosciuta.",
        "not_accepted": "{entities} non ha accettato {target}.",
        "window_long": "Una finestra è aperta da più di {minutes} min.",
        "device_unavailable": "{entity} non è disponibile da più di {minutes} min.",
        "sensor_unavailable_device": "I sensori di temperatura non sono disponibili; si usa il sensore del dispositivo.",
        "sensor_unavailable_eco": "I sensori di temperatura non sono disponibili; si usa eco.",
        "sensor_silent": "{entity} non invia una temperatura da più di {hours} h; la stanza è regolata su un valore vecchio. Controlla la batteria e il segnale.",
        "sensor_silent_left_out": "{entity} non invia una temperatura da più di {hours} h; viene escluso finché non torna a inviare. Controlla la batteria e il segnale.",
        "no_effect": "Scalda da {hours} h, ma la temperatura è salita solo di {rise}° (ne erano previsti circa {expected}°). Controlla la valvola, la fonte di calore e le finestre.",
        "schedule_invalid": "Il programma non è valido ({error}); si usa il programma predefinito.",
        "schedule_gap": "Nessun profilo di programma attivo: {days}; in quei giorni la stanza resta in antigelo.",
        "battery_low": "Batteria scarica su {device} ({level}%).",
        "device_limit_max": "{entity} accetta al massimo {value}: alza la sua temperatura massima sul dispositivo se la stanza ha bisogno di più.",
        "device_limit_min": "{entity} accetta almeno {value}: abbassa la sua temperatura minima sul dispositivo per un antigelo più basso.",
        "weather_without_source": "Attivo ma senza effetto senza un sensore di temperatura esterna o un'entità meteo: {features}.",
        "boiler_min_rooms": "Servono {needed} stanze per accendere la fonte di calore, ma la casa ha solo {rooms} stanze che possono accenderla: la fonte si accende solo per l'antigelo.",
        "outdoor_unavailable": "Nessuna temperatura esterna da {entities} da più di {minutes} min: lo spegnimento, la stagione automatica, la compensazione e lo spegnimento ottimale non possono usarla.",
        "auto_vacation_on": "Sono tutti fuori da molto tempo: è iniziata la vacanza automatica.",
        "auto_vacation_off": "La vacanza automatica è finita.",
        "frost_protection": "La stanza è a {current}°, sotto la temperatura antigelo ({frost}°): il riscaldamento non riesce a mantenerla.",
        "mold_risk": "Rischio muffa: la parete più fredda ha raggiunto circa {surface}% di umidità (stanza {humidity}%). Arieggiare e tenere la stanza un po' più calda riducono il rischio.",
        "pause_long": "Il riscaldamento è in pausa da più di {hours} h: funziona solo l'antigelo.",
        "season_on": "La stagione di riscaldamento è iniziata.",
        "season_off": "La stagione di riscaldamento è finita: niente riscaldamento finché non ricomincia.",
        "guest_ended": "La modalità ospiti si è spenta da sola: la casa segue di nuovo le persone.",
        "vacation_started": "La vacanza è iniziata: tutte le stanze sono su away.",
        "vacation_preheat": "La vacanza finisce presto: la casa si scalda per il vostro rientro.",
        "resolved_source_unavailable": "La fonte di calore {entity} funziona di nuovo.",
        "resolved_source_unavailable_other": "La fonte di calore {entity} funziona di nuovo.",
        "resolved_circuit_unavailable": "Il relè di circuito {entity} funziona di nuovo.",
        "resolved_device_unavailable": "{entity} è di nuovo disponibile.",
        "resolved_sensor_unavailable": "I sensori di temperatura funzionano di nuovo.",
        "resolved_sensor_silent": "{entity} invia di nuovo la temperatura.",
        "resolved_no_effect": "La stanza si scalda di nuovo.",
        "resolved_outdoor_unavailable": "La temperatura esterna è di nuovo disponibile.",
        "resolved_window_long": "La finestra è di nuovo chiusa.",
        "resolved_battery_low": "La batteria di {device} è di nuovo a posto.",
        "resolved_not_accepted": "{entities} segue di nuovo l'obiettivo.",
        "resolved_frost_protection": "La stanza è tornata alla temperatura antigelo.",
        "resolved_mold_risk": "Il rischio muffa è passato: le pareti sono di nuovo abbastanza asciutte.",
        "free_days": "giorni liberi (festivi)",
        "weekend_workdays": "giorni lavorativi nel fine settimana",
        "wf_cutoff": "spegnere il riscaldamento quando fa caldo",
        "wf_season_auto": "stagione automatica",
        "wf_compensation": "compensazione esterna",
        "wf_window_ignore": "ignorare le finestre sopra",
        "wf_forecast": "usare le previsioni (servono un'entità meteo e lo spegnimento)",
    },
}

WEEKDAYS: dict[str, dict[str, str]] = {
    "en": {
        "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
        "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
    },
    "ro": {
        "mon": "luni", "tue": "marți", "wed": "miercuri", "thu": "joi",
        "fri": "vineri", "sat": "sâmbătă", "sun": "duminică",
    },
    "de": {
        "mon": "Montag", "tue": "Dienstag", "wed": "Mittwoch", "thu": "Donnerstag",
        "fri": "Freitag", "sat": "Samstag", "sun": "Sonntag",
    },
    "nl": {
        "mon": "maandag", "tue": "dinsdag", "wed": "woensdag", "thu": "donderdag",
        "fri": "vrijdag", "sat": "zaterdag", "sun": "zondag",
    },
    "fr": {
        "mon": "lundi", "tue": "mardi", "wed": "mercredi", "thu": "jeudi",
        "fri": "vendredi", "sat": "samedi", "sun": "dimanche",
    },
    "it": {
        "mon": "lunedì", "tue": "martedì", "wed": "mercoledì", "thu": "giovedì",
        "fri": "venerdì", "sat": "sabato", "sun": "domenica",
    },
}  # fmt: skip


def language(hass_language: str | None) -> str:
    """The language of the texts: the one of Home Assistant when there are
    texts in it, English otherwise."""
    lang = str(hass_language or "").lower()[:2]
    return lang if lang in TEXTS else "en"


def category(code: str | None) -> str:
    """How much an alert matters (an unknown one is a warning)."""
    return CATEGORIES.get(str(code), CATEGORY_WARNING)


def _values(lang: str, code: str, params: dict[str, Any]) -> dict[str, str]:
    """The values of an alert as text."""
    texts = TEXTS[lang]
    values = {k: str(v) for k, v in params.items()}
    if isinstance(params.get("entities"), list):
        values["entities"] = ", ".join(str(e) for e in params["entities"])
    if isinstance(params.get("rooms"), list):
        values["rooms"] = ", ".join(
            f"{name} (−{gap}°)" for name, gap in params["rooms"] if name is not None
        )
    if isinstance(params.get("features"), list):
        values["features"] = ", ".join(texts.get(f"wf_{f}", str(f)) for f in params["features"])
    if code == "schedule_gap":
        days = [WEEKDAYS[lang].get(str(d), str(d)) for d in params.get("days") or []]
        if params.get("free_days"):
            days.append(texts["free_days"])
        if params.get("workdays"):
            days.append(texts["weekend_workdays"])
        values["days"] = ", ".join(days)
    return values


def alert_text(
    lang: str,
    code: str | None,
    params: dict[str, Any] | None,
    fallback: str,
    *,
    resolved: bool = False,
) -> str:
    """The text of an alert (or of its end) in a language; ``fallback`` when unknown."""
    if not code:
        return fallback
    params = params or {}
    key = code
    if code == "sensor_unavailable" and not resolved:
        key = f"sensor_unavailable_{params.get('fallback') or 'device'}"
    if code == "sensor_silent" and params.get("left_out"):
        key = "sensor_silent_left_out"
    if resolved:
        key = f"resolved_{code}"
    template = TEXTS[lang].get(key)
    if template is None:
        return fallback
    try:
        return template.format(**_values(lang, code, params))
    except (KeyError, IndexError, ValueError, TypeError):
        return fallback


def parse_time(value: Any) -> time | None:
    """A time of the options ("HH:MM[:SS]"), None when empty or invalid."""
    if not value:
        return None
    try:
        parts = [int(p) for p in str(value).split(":")]
        return time(parts[0], parts[1] if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        return None


def in_quiet_hours(local_now: datetime, start: time | None, end: time | None) -> bool:
    """True in the quiet hours (they may go past midnight; equal times: none)."""
    if start is None or end is None or start == end:
        return False
    now = local_now.time().replace(second=0, microsecond=0)
    if start < end:
        return start <= now < end
    return now >= start or now < end


def targets(value: Any) -> list[str]:
    """The recipients chosen for a category, as written (duplicates dropped).

    A recipient is a notify service or entity, optionally followed by the email
    addresses it sends to: ``notify.me_gmail_com: ana@example.com, ion@example.com``
    (Google Mail and other mail services need them).
    """
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    result = []
    for item in value:
        item = str(item).strip()
        if not item:
            continue
        name, _, addresses = item.partition(":")
        # Services and entities are lower case (a phone keyboard may write "Notify.").
        name = name.strip().lower()
        if "." not in name:
            name = f"notify.{name}"
        recipient = f"{name}: {addresses.strip()}" if addresses.strip() else name
        if recipient not in result:
            result.append(recipient)
    return result


def split_recipient(recipient: str) -> tuple[str, list[str]]:
    """The notify service or entity of a recipient and its email addresses."""
    name, _, addresses = recipient.partition(":")
    found = [a.strip() for a in addresses.replace(";", ",").split(",") if a.strip()]
    return name.strip().lower(), found


def invalid_recipient(recipient: str) -> str | None:
    """The first part of a recipient that cannot be used, None when it is fine."""
    name, addresses = split_recipient(recipient)
    if not name.startswith("notify.") or len(name) <= len("notify.") or " " in name:
        return name or recipient
    for address in addresses:
        local, at, domain = address.partition("@")
        if not at or not local or "." not in domain or " " in address:
            return address
    return None
