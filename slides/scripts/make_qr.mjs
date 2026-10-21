// One-off generator for the QR codes on the *Want to know more?* slide.
//
// Output is an SVG in `public/` and it IS committed: it is a few kilobytes of
// text, it never changes unless the URL changes, and committing it keeps
// `npm run build` free of a code-generation step. Re-run by hand after a
// rename:
//   node scripts/make_qr.mjs                                                  (repository)
//   node scripts/make_qr.mjs https://www.conterra.de/newsletter public/qr-newsletter.svg
//
// Usage: node scripts/make_qr.mjs [url] [outfile]

import { writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import QRCode from 'qrcode'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const url = process.argv[2] ?? 'https://github.com/m-scherpi/euro_dev_summit_26_test_data_ai'
const out = resolve(root, process.argv[3] ?? 'public/qr-repo.svg')

const svg = await QRCode.toString(url, {
  type: 'svg',
  errorCorrectionLevel: 'M',
  margin: 1,
  color: { dark: '#111111', light: '#00000000' },
})
writeFileSync(out, svg)
console.log(`make_qr: ${url} -> ${out} (${svg.length} bytes)`)
