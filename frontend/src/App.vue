<template>
  <router-view />
  <div class="recorder-widget" :class="{ recording: isRecording }">
    <button class="record-btn" @click="toggleRecording" :title="isRecording ? 'Stop Recording' : 'Record Session'">
      <span class="record-dot" :class="{ active: isRecording }"></span>
      <span v-if="!isRecording" class="record-label">Record</span>
      <span v-else class="record-label">{{ recordingTime }} - Stop</span>
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const isRecording = ref(false)
const recordingTime = ref('00:00')
let mediaRecorder = null
let recordedChunks = []
let recordingTimer = null
let recordingSeconds = 0

const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0')
  const s = (seconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

const toggleRecording = async () => {
  if (isRecording.value) {
    stopRecording()
  } else {
    await startRecording()
  }
}

const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: false
    })

    recordedChunks = []
    recordingSeconds = 0
    recordingTime.value = '00:00'

    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : 'video/webm'
    mediaRecorder = new MediaRecorder(stream, { mimeType })

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        recordedChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = () => {
      const blob = new Blob(recordedChunks, { type: 'video/webm' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `infer-session-${new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-')}.webm`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      stream.getTracks().forEach(track => track.stop())
      clearInterval(recordingTimer)
      isRecording.value = false
      recordingTime.value = '00:00'
    }

    stream.getVideoTracks()[0].onended = () => {
      if (isRecording.value) {
        stopRecording()
      }
    }

    mediaRecorder.start(1000)
    isRecording.value = true

    recordingTimer = setInterval(() => {
      recordingSeconds++
      recordingTime.value = formatTime(recordingSeconds)
    }, 1000)

  } catch (err) {
    console.error('Screen recording failed:', err)
  }
}

const stopRecording = () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@100..800&family=Space+Grotesk:wght@300..700&display=swap');

:root {
  --bg-primary: #0a0e1a;
  --bg-secondary: #0f1528;
  --bg-tertiary: #141c33;
  --bg-card: #111827;
  --bg-elevated: #1a2340;
  --border-primary: #1e2d4a;
  --border-secondary: #2a3a5c;
  --border-accent: #3b82f6;
  --text-primary: #f0f4ff;
  --text-secondary: #94a3c4;
  --text-muted: #5a6a8a;
  --accent-blue: #3b82f6;
  --accent-cyan: #06b6d4;
  --accent-glow: rgba(59, 130, 246, 0.15);
  --accent-gradient: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
  --white: #ffffff;
  --danger: #ef4444;
  --success: #10b981;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Inter', 'Space Grotesk', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--text-primary);
  background-color: var(--bg-primary);
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
  background: var(--border-secondary);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--accent-blue);
}

button {
  font-family: inherit;
}

input, textarea, select {
  font-family: inherit;
}

a {
  color: var(--accent-blue);
  text-decoration: none;
}

a:hover {
  color: var(--accent-cyan);
}

.recorder-widget {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 10000;
}

.record-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 24px;
  color: var(--text-primary);
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  font-weight: 600;
  transition: all 0.3s;
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.record-btn:hover {
  border-color: var(--accent-blue);
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(59, 130, 246, 0.2);
}

.recorder-widget.recording .record-btn {
  border-color: var(--danger);
  background: rgba(239, 68, 68, 0.1);
}

.record-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: all 0.3s;
}

.record-dot.active {
  background: var(--danger);
  animation: recordPulse 1s ease-in-out infinite;
}

@keyframes recordPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}

.record-label {
  white-space: nowrap;
}
</style>
