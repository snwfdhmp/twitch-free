import Docker from "dockerode"
import express from "express"
import fs from "fs"
const app = express()
const docker = new Docker()

// use __dirname
const __dirname = new URL(".", import.meta.url).pathname

const log = (data) => {
  console.log(`${new Date().toISOString()} ${data.toString()}`)
}

const CACHE_PATH = __dirname + "cache.json"
let cache = {}

const pushCache = (key, value) => {
  cache[key] = value
  writeCacheToDisk()
}

const debounce = (func, delay) => {
  let timer
  return function (...args) {
    clearTimeout(timer)
    timer = setTimeout(() => func.apply(this, args), delay)
  }
}

const writeCacheToDisk = debounce(async () => {
  // write cache to disk
  return await fs.promises.writeFile(CACHE_PATH, JSON.stringify(cache))
}, 4000)

const loadCacheFromDisk = async () => {
  try {
    const data = await fs.promises.readFile(CACHE_PATH)
    cache = JSON.parse(data)
  } catch (e) {
    console.error(e)
  }
}

const getUrl = (inputUrl) => {
  return new Promise(async (resolve, reject) => {
    if (cache[inputUrl]) {
      if (cache[inputUrl].expiresAt < Date.now()) {
        delete cache[inputUrl]
      } else {
        log(`served from cache: ${cache[inputUrl].url}`)
        resolve(cache[inputUrl].url)
        return
      }
    }

    // Crée le conteneur avec l'image souhaitée
    const container = await docker.createContainer({
      Image: "twitch-vod-recovery-v3", // Remplace par l'image souhaitée
      Cmd: ["python", "vod_recovery.py", inputUrl], // Par exemple : attend des données et les retourne
      AttachStdin: true,
      AttachStdout: true,
      AttachStderr: true,
      OpenStdin: true,
      Tty: false,
    })

    log("Container created")

    // Démarre le conteneur
    await container.start()

    log("Container started")

    // Récupère le stream d'entrée/sortie du conteneur
    const stream = await container.attach({
      stream: true,
      stdin: true,
      stdout: true,
      stderr: true,
    })

    // Envoie les données à `stdin`

    const inputData = []
    let inputIndex = 0

    // Ecoute les données de `stdout`
    stream.on("data", async (data) => {
      // log("Output:", data.toString())
      if (inputIndex !== inputData.length) {
        stream.write(inputData[inputIndex] + "\n")
        inputIndex++
        return
      }

      const REGEX_URL =
        /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/
      // extract url
      log("------ DATA START ------")
      log(data.toString())
      log("------ DATA END ------")
      const url = data.toString().match(REGEX_URL)
      log(url[0])
      resolve(url[0])
      pushCache(inputUrl, {
        url: url[0],
        expiresAt: Date.now() + 1000 * 60 * 60 * 48,
      })
      await container.stop()
      await container.remove()
      log("Container stopped and removed")
    })

    // Ecoute les données de `stderr`
    stream.on("error", (data) => {
      console.error("Error:", data.toString())
    })
  })
}

app.get("/", (req, res) => {
  // serve public.html
  res.sendFile(__dirname + "public.html")
})
app.get("/videos/:id", async (req, res) => {
  const ip =
    req.headers["x-forwarded-for"] ||
    req.headers["x-real-ip"] ||
    req.connection.remoteAddress ||
    "unknown-ip"
  log(`[${ip}] requested https://twitch.tv/videos/${req.params.id}`)

  // get /:id
  const id = req.params.id
  const url = `https://twitch.tv/videos/${id}`

  // detect if ?vlc=1
  const isVlc = req.query.vlc === "true" || req.query.vlc === "1"

  try {
    const videoUrl = await getUrl(url)
    // redirect
    if (isVlc) {
      res.redirect(`vlc-x-callback://x-callback-url/stream?url=${videoUrl}`)
      return
    }
    // redirect
    res.redirect(videoUrl)
  } catch (e) {
    console.error(e)
    res.status(500).send(e)
  }
})

await loadCacheFromDisk()

const SERVER_PORT = 7359
app.listen(SERVER_PORT, () => {
  console.log(`Server started on port ${SERVER_PORT}`)
})
