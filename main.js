import Docker from "dockerode"
import express from "express"
import fs from "fs"
import axios from "axios"
const app = express()
const docker = new Docker()

// use __dirname
const __dirname = new URL(".", import.meta.url).pathname

const log = (data) => {
  console.log(`${new Date().toISOString()} ${data.toString()}`)
}

// const CACHE_PATH = __dirname + "cache.json"
// let cache = {}

// const pushCache = (key, value) => {
//   cache[key] = value
//   writeCacheToDisk()
// }

const debounce = (func, delay) => {
  let timer
  return function (...args) {
    clearTimeout(timer)
    timer = setTimeout(() => func.apply(this, args), delay)
  }
}

// const writeCacheToDisk = debounce(async () => {
//   // write cache to disk
//   return await fs.promises.writeFile(CACHE_PATH, JSON.stringify(cache, null, 2))
// }, 4000)

// const loadCacheFromDisk = async () => {
//   try {
//     const data = await fs.promises.readFile(CACHE_PATH)
//     cache = JSON.parse(data)
//   } catch (e) {
//     console.error(e)
//   }
// }

const getUrl = (id) => {
  return new Promise(async (resolve, reject) => {
    // if (cache[id]) {
    //   if (cache[id].expiresAt < Date.now()) {
    //     delete cache[id]
    //   } else {
    //     log(`served from cache: ${cache[id]}`)
    //     resolve(cache[id].url)
    //     return
    //   }
    // }

    const { data } = await axios.post(
      "https://gql.twitch.tv/gql",
      {
        query: `query { video(id: "${id}") { title, broadcastType, createdAt, seekPreviewsURL, owner { login } } }`,
      },
      {
        headers: {
          "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        timeout: 30000,
      }
    )

    console.log(data)
    const vodData = data.data.video
    const currentUrl = new URL(vodData.seekPreviewsURL)
    const domain = currentUrl.hostname
    const paths = currentUrl.pathname.split("/")
    const vodSpecialId =
      paths[paths.indexOf(paths.find((i) => i.includes("storyboards"))) - 1]
    const url = `https://${domain}/${vodSpecialId}/chunked/index-dvr.m3u8`
    console.log(`Found: ${url}`)
    resolve(url)

    // cache[id] = m3u8Url
    // writeCacheToDisk()
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
  const id = req.params.id
  log(`[${ip}] requested https://twitch.tv/videos/${id}`)

  let m3u8Url
  try {
    m3u8Url = await getUrl(id)
  } catch (e) {
    console.error(e)
    res.status(500).send(e)
    return
  }

  const data = await axios.get(m3u8Url)

  if (req.query.vlc) {
    res.redirect(`vlc-x-callback://x-callback-url/stream?url=${m3u8Url}`)
    return
  }

  const m3u8proxyUrl = `https://m3u8.snwfdhmp.com/m3u8-proxy?url=${encodeURIComponent(
    m3u8Url
  )}`

  console.log(`Redirecting to ${m3u8proxyUrl}`)

  // serve public.template.html but replace __M3U8URLREPLACE__ with m3u8Url
  res.header("Access-Control-Allow-Origin", "*")
  res.header("Access-Control-Allow-Methods", "*")
  res.header("Access-Control-Allow-Headers", "*")
  res.send(
    fs
      .readFileSync(__dirname + "public.template.html", "utf8")
      .replaceAll("__M3U8URLREPLACE__", m3u8proxyUrl)
  )

  return

  // res.redirect(m3u8Url) // FORMER CODE TO REDIRECT TO M3U8
})

// app.get("/m3u8/:id", (req, res) => {
// res.json(cache)
// })

// await loadCacheFromDisk()

const SERVER_PORT = 7359
app.listen(SERVER_PORT, () => {
  console.log(`Server started on port ${SERVER_PORT}`)
})
