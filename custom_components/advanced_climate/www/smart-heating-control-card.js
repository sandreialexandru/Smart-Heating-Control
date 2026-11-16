/*
 * Smart Heating Control card: the dashboard resource (the same URL as before).
 *
 * The card itself is in shc/, served from a folder with the version in its
 * path, so after an update every browser and the companion app load the new
 * files. Only static imports: an open tab has everything it needs once loaded,
 * also after Home Assistant stops serving the folder of the old version.
 * What the card exports is passed on for its tests (tests/card/page.html).
 */
export * from "/advanced_climate/2.7.0a6/shc/card.js";
