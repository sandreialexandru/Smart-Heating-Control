// The chart by mouse and touch: drag, zoom, the navigation bar.

export const ChartInteractMixin = (Base) =>
  class extends Base {
    /** Start a pan or pinch on the chart; True when the pointer is on a chart. */
    _chartPointerDown(ev) {
      const chart = ev.target.closest?.(".hchart");
      if (!chart) return false;
      const room = chart.dataset.chart;
      this._ptrs = this._ptrs || new Map();
      this._ptrs.set(ev.pointerId, ev.clientX);
      const d = this._charts?.[room];
      if (!d) return true;
      const card = chart.closest(".chart-card");
      try {
        card.setPointerCapture(ev.pointerId);
      } catch (err) {
        /* ignore */
      }
      const xs = [...this._ptrs.values()];
      this._pan = {
        room,
        card,
        startX: xs.length > 1 ? (xs[0] + xs[1]) / 2 : ev.clientX,
        dist: xs.length > 1 ? Math.abs(xs[0] - xs[1]) : 0,
        v0: d.v0,
        v1: d.v1,
        moved: false,
      };
      return true;
    }

    /** Pan with one finger or mouse, pinch zoom with two; True when handled. */
    _chartPointerMove(ev) {
      const p = this._pan;
      if (!p || !this._ptrs?.has(ev.pointerId)) return false;
      this._ptrs.set(ev.pointerId, ev.clientX);
      const d = this._charts?.[p.room];
      const chart = p.card.querySelector(".hchart");
      if (!d || !chart) return true;
      const rect = chart.getBoundingClientRect();
      const span = p.v1 - p.v0;
      const xs = [...this._ptrs.values()];
      if (xs.length > 1 && p.dist > 10) {
        // Pinch: zoom around the middle of the two fingers.
        const dist = Math.abs(xs[0] - xs[1]);
        const factor = p.dist / Math.max(dist, 10);
        const center = p.v0 + ((p.startX - rect.left) / rect.width) * span;
        p.moved = true;
        this._setView(p.room, center - (center - p.v0) * factor, center + (p.v1 - center) * factor, true);
        return true;
      }
      // One finger or the mouse moves the values cursor (the bar under the chart pans).
      if (Math.abs(ev.clientX - p.startX) > 4) p.moved = true;
      return false;
    }

    /** Bar under a zoomed chart: drag the window (or tap a place) to move the chart. */
    _navPointerDown(ev) {
      const nav = ev.target.closest?.(".navbar");
      if (!nav) return false;
      const room = nav.dataset.nav;
      const d = this._charts?.[room];
      if (!d) return true;
      ev.preventDefault();
      const card = nav.closest(".chart-card");
      try {
        card.setPointerCapture(ev.pointerId);
      } catch (err) {
        /* ignore */
      }
      const rect = nav.getBoundingClientRect();
      const at = d.t0 + ((ev.clientX - rect.left) / rect.width) * (d.t1 - d.t0);
      const span = d.v1 - d.v0;
      // On the window: keep where it was grabbed; elsewhere: centre the window there.
      const grab = at >= d.v0 && at <= d.v1 ? at - d.v0 : span / 2;
      this._nav = { room, card, grab, span, pointer: ev.pointerId };
      this._navAt = Date.now();
      this._setView(room, at - grab, at - grab + span);
      return true;
    }

    _navPointerMove(ev) {
      const n = this._nav;
      if (!n || ev.pointerId !== n.pointer) return false;
      const d = this._charts?.[n.room];
      const nav = n.card.querySelector(".navbar");
      if (!d || !nav) return true;
      const rect = nav.getBoundingClientRect();
      const at = d.t0 + ((ev.clientX - rect.left) / rect.width) * (d.t1 - d.t0);
      this._setView(n.room, at - n.grab, at - n.grab + n.span, true);
      return true;
    }

    /** End a pan or pinch; a tap without moving shows the values under it. */
    _chartPointerUp(ev) {
      if (!this._ptrs) return;
      this._ptrs.delete(ev.pointerId);
      const p = this._pan;
      if (!this._ptrs.size) this._pan = null;
      else if (p) {
        // One finger left after a pinch: start a new pan from here.
        const d = this._charts?.[p.room];
        const [x] = [...this._ptrs.values()];
        this._pan = { ...p, startX: x, dist: 0, v0: d?.v0 ?? p.v0, v1: d?.v1 ?? p.v1 };
      }
      const chart = p?.card?.querySelector(".hchart");
      if (p && !p.moved && chart) this._chartHover({ type: "pointermove", clientX: ev.clientX, target: chart });
    }

    /**
     * A finger on a chart: its navigation bar shows (``on``); after the finger
     * leaves, the bar, the line and the values under it hide again a moment later.
     */
    _touch(card, on) {
      clearTimeout(this._touchTimer);
      const room = card.dataset.chartcard;
      if (on) {
        this._touched = room;
        card.classList.add("touching");
        return;
      }
      this._touchTimer = setTimeout(() => {
        this._touched = null;
        const now = this.shadowRoot.querySelector(`[data-chartcard="${CSS.escape(room)}"]`);
        if (!now) return;
        now.classList.remove("touching");
        now.querySelectorAll(".cross, .tip").forEach((el) => (el.hidden = true));
      }, 2500);
    }

    /**
     * Ctrl + wheel or touchpad pinch zooms the chart around the pointer; a
     * sideways scroll (or Shift + wheel) moves it through the history.
     */
    _chartWheel(ev) {
      const chart = ev.target.closest?.(".hchart");
      if (!chart) return;
      if (!(ev.ctrlKey || ev.metaKey)) {
        const sideways = Math.abs(ev.deltaX) > Math.abs(ev.deltaY) ? ev.deltaX : ev.shiftKey ? ev.deltaY : 0;
        if (!sideways) return; // the page scrolls normally
        ev.preventDefault();
        const d = this._charts?.[chart.dataset.chart];
        if (!d) return;
        const shift = (sideways / chart.getBoundingClientRect().width) * (d.v1 - d.v0);
        this._setView(chart.dataset.chart, d.v0 + shift, d.v1 + shift, true);
        return;
      }
      // Only pinch on a touchpad or Ctrl + wheel zoom, so the page still scrolls normally.
      ev.preventDefault();
      const d = this._charts?.[chart.dataset.chart];
      if (!d) return;
      const rect = chart.getBoundingClientRect();
      const center = d.v0 + ((ev.clientX - rect.left) / rect.width) * (d.v1 - d.v0);
      this._zoom(chart.dataset.chart, ev.deltaY > 0 ? 1.25 : 0.8, center, true);
    }

    /** Double click zooms in around the pointer. */
    _chartDblClick(ev) {
      // With the pointer captured by the chart card the event target is the card itself.
      const chart = ev.target.closest?.(".hchart") || ev.target.closest?.(".chart-card")?.querySelector(".hchart");
      if (ev.target.closest?.(".zoombar")) return;
      // Two taps on the bar under the chart move it; they do not zoom.
      if (ev.target.closest?.(".navbar") || Date.now() - (this._navAt || 0) < 700) return;
      if (!chart) return;
      const d = this._charts?.[chart.dataset.chart];
      if (!d) return;
      const rect = chart.getBoundingClientRect();
      const center = d.v0 + ((ev.clientX - rect.left) / rect.width) * (d.v1 - d.v0);
      this._zoom(chart.dataset.chart, 0.4, center);
    }
  };
