async function fetchJSON(url) {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }
  return response.json()
}

async function loadStatus() {
  try {
    const status = await fetchJSON('/api/status')

    document.getElementById('runtime-title').textContent = 'Runtime online'
    document.getElementById('runtime-subtitle').textContent = `Ollama host: ${status.config.ollama_host}`

    document.getElementById('platform-value').textContent = `${status.platform.system} ${status.platform.release}`

    document.getElementById('ffmpeg-value').textContent = status.dependencies.ffmpeg ? 'Detected' : 'Missing'

    document.getElementById('ollama-value').textContent = status.dependencies.ollama_server_running
      ? 'Connected'
      : 'Offline'

    document.getElementById('nvidia-value').textContent = status.dependencies.nvidia_smi
      ? 'Detected'
      : 'Not detected'

  } catch (error) {
    document.getElementById('runtime-title').textContent = 'Runtime offline'
    document.getElementById('runtime-subtitle').textContent = error.message
  }
}

async function loadLogs() {
  try {
    const logs = await fetchJSON('/api/logs')

    const output = logs.lines?.length
      ? logs.lines.join('\n')
      : 'No runtime logs yet.'

    document.getElementById('log-output').textContent = output
  } catch (error) {
    document.getElementById('log-output').textContent = `Failed to load logs: ${error.message}`
  }
}

async function loadModels() {
  try {
    const data = await fetchJSON('/api/models')

    const list = document.getElementById('models-list')
    list.innerHTML = ''

    if (!data.ok || !data.models.length) {
      const item = document.createElement('li')
      item.textContent = 'No local models detected.'
      list.appendChild(item)
      return
    }

    for (const model of data.models) {
      const item = document.createElement('li')
      item.textContent = model
      list.appendChild(item)
    }
  } catch (error) {
    document.getElementById('models-list').innerHTML = `<li>${error.message}</li>`
  }
}

async function refresh() {
  await Promise.all([
    loadStatus(),
    loadLogs(),
    loadModels(),
  ])
}

refresh()
setInterval(refresh, 5000)
