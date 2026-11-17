// The rooms of the panel in groups: by floor (the floor of the area of Home
// Assistant the room is in) or by heating circuit (the relay of its circuit),
// as chosen in the panel; or one group of all of them.

export const GROUP_MODES = ["none", "floor", "circuit"];

export const GroupsMixin = (Base) =>
  class extends Base {
    /** The floor of a room: {key, name, level} or null (no area, or an area on no floor). */
    _roomFloor(a) {
      const floorId = a.area ? this._hass.areas?.[a.area]?.floor_id : null;
      const floor = floorId ? this._hass.floors?.[floorId] : null;
      return floor ? { key: floorId, name: floor.name || floorId, level: floor.level ?? 0 } : null;
    }

    /** The circuit of a room: {key, name} or null. */
    _roomCircuit(a) {
      if (!a.circuit) return null;
      return { key: a.circuit, name: this._hass.states[a.circuit]?.attributes?.friendly_name || a.circuit, level: 0 };
    }

    /** The ways of grouping the rooms there are: floors only with rooms on floors, circuits only with circuits. */
    _groupModes(rooms) {
      const attrs = rooms.map((r) => r.attributes);
      return GROUP_MODES.filter(
        (m) =>
          m === "none" ||
          (m === "floor" && attrs.some((a) => this._roomFloor(a))) ||
          (m === "circuit" && attrs.some((a) => a.circuit))
      );
    }

    /** The grouping in use (one that is there). */
    _groupMode(rooms) {
      const modes = this._groupModes(rooms);
      return modes.includes(this._group) ? this._group : "none";
    }

    /**
     * The rooms in groups: [{key, name, rooms}], in the order of the floors
     * (their level) or of the circuits (their name); the rooms of none last.
     * Without grouping: one group, without a name.
     */
    _roomGroups(rooms, mode) {
      if (mode === "none") return [{ key: "", name: null, rooms }];
      const of = (a) => (mode === "floor" ? this._roomFloor(a) : this._roomCircuit(a));
      const groups = new Map();
      for (const r of rooms) {
        const g = of(r.attributes);
        const key = g ? g.key : "";
        if (!groups.has(key)) {
          groups.set(key, {
            key,
            name: g ? g.name : this._t(mode === "floor" ? "gr_no_floor" : "gr_no_circuit"),
            level: g ? g.level : Infinity,
            rooms: [],
          });
        }
        groups.get(key).rooms.push(r);
      }
      return [...groups.values()].sort((x, y) => x.level - y.level || String(x.name).localeCompare(String(y.name)));
    }

    /** The group of a room, as a function: room_id → group key (for lists of other things than rooms). */
    _groupOf(rooms, mode) {
      const map = new Map();
      for (const g of this._roomGroups(rooms, mode)) for (const r of g.rooms) map.set(r.attributes.room_id, g);
      return (roomId) => map.get(roomId);
    }
  };
