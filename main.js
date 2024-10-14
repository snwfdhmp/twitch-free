import Docker from "dockerode"
import express from "express"
const app = express()
const docker = new Docker()

const log = (data) => {
  console.log(`${new Date().toISOString()} ${data.toString()}`)
}

const getUrl = (inputUrl) => {
  return new Promise(async (resolve, reject) => {
    // Crée le conteneur avec l'image souhaitée
    const container = await docker.createContainer({
      Image: "twitch-vod-recovery", // Remplace par l'image souhaitée
      Cmd: ["python", "vod_recovery.py"], // Par exemple : attend des données et les retourne
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

    const inputData = ["3", "3", inputUrl]
    let inputIndex = 0

    // Ecoute les données de `stdout`
    stream.on("data", async (data) => {
      // log("Output:", data.toString())
      if (inputIndex === inputData.length) {
        const REGEX_URL =
          /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/
        // extract url
        const url = data.toString().match(REGEX_URL)
        log(url[0])
        resolve(url[0])
        await container.stop()
        await container.remove()
        log("Container stopped and removed")
      }
      stream.write(inputData[inputIndex] + "\n")
      inputIndex++
    })

    // Ecoute les données de `stderr`
    stream.on("error", (data) => {
      console.error("Error:", data.toString())
    })
  })
}

app.get("/videos/:id", async (req, res) => {
  // get /:id
  const id = req.params.id
  const url = `https://twitch.tv/videos/${id}`

  try {
    const videoUrl = await getUrl(url)
    // redirect
    res.redirect(videoUrl)
  } catch (e) {
    console.error(e)
    res.status(500).send(e)
  }
})

const SERVER_PORT = 7358
app.listen(SERVER_PORT, () => {
  console.log(`Server started on port ${SERVER_PORT}`)
})
