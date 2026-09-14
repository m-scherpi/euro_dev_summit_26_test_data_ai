// Copies the result screenshots from the use-case `input/` folders into
// `public/img/`, because Vite only serves assets from inside the project root.
//
// `public/img/` is therefore generated and gitignored: every PNG is already in
// git once, at its source of truth next to the data it shows. Run via the
// `predev` / `prebuild` npm hooks so it cannot be forgotten.
//
// The screenshots carry their basemap attribution burnt into the bottom edge
// (Esri / TomTom / Garmin / USGS / FAO / NOAA, plus Land NRW on the stations and
// rent-census images). Publishing them is redistribution, so that bar must stay
// visible -- never crop it.
//
// The rent-census capture is the Map Viewer's own export and is ~8 MB, several
// times the others. It is copied as-is rather than downscaled: no image tool is
// a dependency of this deck, and re-encoding somebody else's attribution bar is
// exactly the operation that loses it.

import { copyFileSync, mkdirSync, statSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

/** Screenshots to publish, with the use case that produced them. */
const ASSETS = [
  { from: '../csv_data/input/nrw_points.png', to: 'public/img/nrw_points.png' },
  { from: '../csv_data/input/germany_points_10k.png', to: 'public/img/germany_points_10k.png' },
  { from: '../open_data_search/input/nrw_stations.png', to: 'public/img/nrw_stations.png' },
  { from: '../portal_publish/input/class_breaks.png', to: 'public/img/muenster_rent_class_breaks.png' },
]

let bytes = 0
for (const asset of ASSETS) {
  const from = resolve(root, asset.from)
  const to = resolve(root, asset.to)
  mkdirSync(dirname(to), { recursive: true })
  copyFileSync(from, to)
  const size = statSync(to).size
  bytes += size
  console.log(`  ${asset.from} -> ${asset.to} (${(size / 1024 / 1024).toFixed(2)} MB)`)
}
console.log(`sync-assets: ${ASSETS.length} screenshots, ${(bytes / 1024 / 1024).toFixed(2)} MB total`)
