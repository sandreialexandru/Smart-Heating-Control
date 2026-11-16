// What the card and the panel share: every part of the house and the rooms,
// their events and drawing. A change made in a module shows in both.

import { ChartMixin } from "../chart/chart.js";
import { ChartDataMixin } from "../chart/data.js";
import { ChartInteractMixin } from "../chart/interact.js";
import { HouseMixin } from "../house/house.js";
import { AlertsMixin } from "../room/alerts.js";
import { CompactMixin } from "../room/compact.js";
import { DetailsMixin } from "../room/details.js";
import { GaugeMixin } from "../room/gauge.js";
import { QuickMixin } from "../room/quick.js";
import { ReasonMixin } from "../room/reason.js";
import { RoomMixin } from "../room/room.js";
import { ScheduleMixin } from "../schedule/editor.js";
import { ProfilesMixin } from "../schedule/profiles.js";
import { EventsMixin } from "./events.js";
import { FormatMixin } from "./format.js";
import { HaMixin } from "./ha.js";
import { HostMixin } from "./host.js";
import { IconMixin } from "./icons.js";

const MIXINS = [
  FormatMixin,
  IconMixin,
  HaMixin,
  ChartDataMixin,
  ChartMixin,
  ChartInteractMixin,
  ProfilesMixin,
  ScheduleMixin,
  GaugeMixin,
  ReasonMixin,
  QuickMixin,
  DetailsMixin,
  AlertsMixin,
  RoomMixin,
  CompactMixin,
  HouseMixin,
  EventsMixin,
  HostMixin,
];

/** The base class of the card and the panel (an HTMLElement with every part). */
export const ShcBase = MIXINS.reduce((base, mixin) => mixin(base), HTMLElement);
