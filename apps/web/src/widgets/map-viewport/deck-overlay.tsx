"use client";

import { useEffect } from "react";
import { useControl } from "react-map-gl/maplibre";
import { MapboxOverlay, type MapboxOverlayProps } from "@deck.gl/mapbox";

/** Bridge deck.gl layers onto a MapLibre map instance. */
export function DeckGLOverlay(props: MapboxOverlayProps) {
  const overlay = useControl<MapboxOverlay>(() => new MapboxOverlay(props));

  // Never call setProps during render — that can re-enter MapLibre's render loop
  // ("Attempting to run(), but is already running").
  useEffect(() => {
    overlay.setProps(props);
  });

  return null;
}
