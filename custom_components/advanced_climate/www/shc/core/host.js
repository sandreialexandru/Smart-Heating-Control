// The element that shows houses and rooms (the card, the panel): its state, listeners, updates and drawing by blocks.

export const HostMixin = (Base) =>
  class extends Base {
    /** Event listeners are set once on the shadow root; the content is redrawn by _render. */
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._editing = null;
      this._draft = null;
      this._open = {};
      this._lastKey = "";
      this._error = {};
      this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
      this.shadowRoot.addEventListener("change", (ev) => this._onChange(ev));
      // Whether a mouse button or a finger is down (see _redrawAfterTyping).
      this._pressing = false;
      this.shadowRoot.addEventListener("pointerdown", () => (this._pressing = true), true);
      // On the window (a finger let go outside the card counts too); added while
      // the card is on the page (connectedCallback), so a removed card is freed.
      this._onWindowUp = (ev) => {
        this._pressing = false;
        // A pan let go outside the card (e.g. outside the window) still ends,
        // else the card would stop following Home Assistant.
        if ((this._pan || this._nav) && !ev.composedPath().includes(this)) this._pointerUp(ev);
      };
      this.shadowRoot.addEventListener("toggle", (ev) => this._onToggle(ev), true);
      this.shadowRoot.addEventListener("pointerdown", (ev) => this._pointerDown(ev));
      this.shadowRoot.addEventListener("pointermove", (ev) => this._pointerMove(ev));
      this.shadowRoot.addEventListener("pointerup", (ev) => this._pointerUp(ev));
      this.shadowRoot.addEventListener("pointercancel", (ev) => this._pointerUp(ev));
      this.shadowRoot.addEventListener("wheel", (ev) => this._chartWheel(ev), { passive: false });
      this.shadowRoot.addEventListener("dblclick", (ev) => this._chartDblClick(ev));
      this.shadowRoot.addEventListener("pointerleave", (ev) => this._chartHover(ev), true);
      this.shadowRoot.addEventListener("keydown", (ev) => this._keyDown(ev));
    }

    /** The animations (flame, pulse) stop while the card is not on the screen. */
    connectedCallback() {
      window.addEventListener("pointerup", this._onWindowUp, true);
      window.addEventListener("pointercancel", this._onWindowUp, true);
      if (!this._io && "IntersectionObserver" in window) {
        this._io = new IntersectionObserver((entries) => {
          for (const entry of entries) this.toggleAttribute("offscreen", !entry.isIntersecting);
        });
      }
      this._io?.observe(this);
      clearTimeout(this._leaveTimer);
      // A moved card: its open chart window becomes modal again at once.
      if (this._hass && this._card && this.shadowRoot.querySelector("dialog.chartpop")) this._render();
    }

    disconnectedCallback() {
      this._io?.disconnect();
      window.removeEventListener("pointerup", this._onWindowUp, true);
      window.removeEventListener("pointercancel", this._onWindowUp, true);
      // Leaving the dashboard closes the chart window, so it does not pop up
      // again later. A card only moved (the columns laid out again, e.g. a phone
      // turned) is back at once and keeps it.
      clearTimeout(this._leaveTimer);
      this._leaveTimer = setTimeout(() => {
        if (this.isConnected) return;
        clearTimeout(this._touchTimer);
        this._touched = null;
        if (Object.keys(this._open || {}).some((k) => k.startsWith("chart-") && this._open[k])) this._closeChart();
      }, 1000);
    }

    /** Called on every state change; redraws only when a watched entity changed. */
    set hass(hass) {
      // Back from a lost connection: what could not be read is asked for again.
      if (hass?.connected && this._hass?.connected === false) this._retryFailed();
      this._hass = hass;
      this._housesMemo = null; // computed once per update
      // The scheme of the card background when known (a dark theme may not set darkMode).
      this.style.colorScheme = this._scheme || (hass?.themes?.darkMode ? "dark" : "light");
      if (this._editing || this._pan) return;
      const active = this.shadowRoot.activeElement;
      if (active && ["INPUT", "SELECT"].includes(active.tagName)) return;
      let timed = false;
      let key = this._watched()
        .map((id) => {
          const s = hass.states[id];
          if (s?.attributes?.override?.until) timed = true;
          return s ? `${id}:${s.state}:${s.last_updated}` : id;
        })
        .join("|");
      // A manual change shows the time it has left: drawn again every minute while there is one.
      const minute = timed ? `|${Math.floor(Date.now() / 60000)}` : "";
      key += minute;
      if (key !== this._lastKey) {
        this._lastKey = key;
        this._render(true);
      }
    }

    /** 12 or 24 hour clock, as set in the profile of the user (Time format). */
    _hour12() {
      const format = this._hass?.locale?.time_format;
      if (format === "12") return true;
      if (format === "24") return false;
      // "language": the clock of the language; "system": the one of the browser.
      const locale = format === "system" ? undefined : this._lang();
      const cycle = new Intl.DateTimeFormat(locale, { hour: "numeric" }).resolvedOptions().hourCycle;
      return cycle === "h11" || cycle === "h12";
    }

    /** Add a style sheet to the shadow root (adopted where the browser can). */
    _addStyle(css) {
      const root = this.shadowRoot;
      if ("adoptedStyleSheets" in root && typeof CSSStyleSheet !== "undefined" && "replaceSync" in CSSStyleSheet.prototype) {
        const sheet = new CSSStyleSheet();
        sheet.replaceSync(css);
        root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
      } else {
        const style = document.createElement("style");
        style.textContent = css;
        root.appendChild(style);
      }
    }

    /** Forget every answer that failed (the chart history, the statistics, the history, the next days). */
    _retryFailed() {
      for (const [k, v] of Object.entries(this._hist || {})) if (v.failed) delete this._hist[k];
      for (const [k, v] of Object.entries(this._stats || {})) if (v.failed) delete this._stats[k];
      if (this._historyLog?.failed) this._historyLog = null;
      if (this._weekLog?.failed) this._weekLog = null;
      this._lastKey = ""; // drawn again (and asked again) even if no entity changed
    }

    /** The chart window, once drawn, shown as a modal (Esc closes it). */
    _chartModal() {
      const dlg = this.shadowRoot.querySelector("dialog.chartpop");
      const modal = (d) => {
        try {
          return d.matches(":modal");
        } catch (_err) {
          return d.open; // a browser without :modal
        }
      };
      if (dlg && typeof dlg.showModal === "function" && !modal(dlg)) {
        if (!dlg.__cancel) {
          dlg.__cancel = true;
          dlg.addEventListener("cancel", (ev) => {
            ev.preventDefault();
            this._closeChart();
          });
        }
        if (dlg.open) dlg.close();
        dlg.showModal();
        this._opaque(dlg);
      }
    }

    /** Put the blocks in ``parent``: a block drawn the same as before keeps its element. */
    _patch(parent, blocks) {
      const old = new Map();
      for (const node of parent.children) if (node.__k) old.set(node.__k, node);
      const make = (html) => {
        const tpl = document.createElement("template");
        tpl.innerHTML = html.trim();
        return tpl.content.firstElementChild;
      };
      const nodes = [];
      for (const b of blocks) {
        let node = old.get(b.k);
        if (!node || node.__src !== b.html) {
          node = make(b.html);
          if (!node) continue;
          node.__src = b.html;
          node.__k = b.k;
        }
        if (b.children) this._patch(node, b.children);
        nodes.push(node);
      }
      nodes.forEach((node, i) => {
        if (parent.children[i] !== node) parent.insertBefore(node, parent.children[i] || null);
      });
      while (parent.children.length > nodes.length) parent.lastElementChild.remove();
    }
  };
