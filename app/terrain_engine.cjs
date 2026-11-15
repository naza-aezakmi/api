// Persistent relief worker. FastAPI sends one JSON request per line over stdin.
const { readFileSync, createReadStream } = require('node:fs')
const { join, resolve } = require('node:path')
const { Readable } = require('node:stream')
const { gunzipSync } = require('node:zlib')
const { createInterface } = require('node:readline')

const directory = resolve(process.env.TERRAIN_ATLAS_PATH || join(__dirname, '../terrain-atlas'))
const read = file => readFileSync(join(directory, file), 'utf8')
const manifest = JSON.parse(read('relief/index.json'))
const screen = gunzipSync(readFileSync(join(directory, 'relief/field-screen-v1.gz')))
if (screen.length !== manifest.worlds.earth.count) throw new Error('Invalid field screen')

const fetchFile = async file => new Response(Readable.toWeb(createReadStream(join(directory, file))))
let sourceWindow
let respond
const scope = {
  postMessage(result) {
    if (result.kind === 'loading') return
    if (result.kind === 'results') {
      const { earth } = manifest.worlds
      result = {
        ...result,
        step: manifest.step,
        earth: { label: earth.label, resolution: earth.resolution, radius: earth.radius },
        source: sourceWindow,
      }
    }
    respond?.(result)
  },
}
new Function('fetch', 'self', read('relief-codec.js') + '\n' +
  read('relief-worker.js').replace('importScripts("relief-codec.js");', '') +
  '\nself.cellCenter = point;')(fetchFile, scope)

async function search(request) {
  const { radius, rows, label, resolution } = manifest.worlds[request.planet]
  const latitude = request.lat * Math.PI / 180
  const longitude = ((request.lon + 180) % 360 + 360) % 360 - 180
  const j = Math.floor(radius * latitude / manifest.step)
  const i = Math.abs(request.lat) === 90 ? 0 : Math.floor(radius * longitude * Math.PI / 180 * Math.cos(latitude) / manifest.step)
  const row = rows[rows[0][0] - j]
  if (!row || i < -row[1] || i >= row[1]) return { kind: 'error' }
  const position = row[2] + row[1] + i
  sourceWindow = { ...scope.cellCenter(rows, radius, manifest.step, position), label, resolution }
  return new Promise((accept, reject) => {
    respond = accept
    Promise.resolve(scope.onmessage({ data: {
      id: 1, body: request.planet, position, weights: request.weights, screen,
    } })).catch(reject)
  })
}

async function main() {
  for await (const line of createInterface({ input: process.stdin })) {
    try {
      const result = await search(JSON.parse(line))
      process.stdout.write(JSON.stringify(result) + '\n')
    } catch (error) {
      console.error(error)
      process.stdout.write(JSON.stringify({ kind: 'error' }) + '\n')
    }
  }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
