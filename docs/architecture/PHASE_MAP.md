# Map UI — MapLibre + deck.gl

**Status:** Implemented  
**Route:** `/map`

## Stack
- MapLibre GL (dark basemap via CARTO Dark Matter)
- deck.gl `ScatterplotLayer` + `HeatmapLayer`
- `MapboxOverlay` bridge for MapLibre
- Live GeoJSON from `GET /api/v1/spatial/incidents?bbox=...`

## UX
- Pan/zoom reloads viewport incidents
- Layer mode: points / heatmap / both
- Severity filter
- Click point → inspector panel
- Auth via bearer token from `/login` (`client=api`)

## Install (local)

```bash
cd apps/web
npm install
# or from repo root with pnpm
pnpm install
pnpm --filter @crimelens/web dev
```

Requires API up + migrated + seeded, then sign in.
