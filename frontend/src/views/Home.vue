<template>
  <div class="home-container">
    <nav class="navbar">
      <div class="nav-brand">
        <span class="brand-icon">&#9670;</span>
        INFER
      </div>
      <div class="nav-links">
        <span class="nav-badge">v1.0</span>
        <a href="#" class="github-link">
          Documentation <span class="arrow-icon">&#8599;</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
      <section class="hero-section">
        <div class="hero-left">
          <div class="tag-row">
            <span class="blue-tag">Multi-Agent Prediction Engine</span>
            <span class="version-text">/ Azure OpenAI + GraphRAG</span>
          </div>

          <h1 class="main-title">
            Upload Any Document.<br>
            <span class="gradient-text">Predict What Happens Next.</span>
          </h1>

          <div class="hero-desc">
            <p>
              From a single document, <span class="highlight-white">Infer</span> extracts entities and builds a parallel world of <span class="highlight-blue">autonomous AI agents</span> powered by GPT-4.1. Inject variables, observe emergent behavior, and discover <span class="highlight-code">optimal outcomes</span> in complex social dynamics.
            </p>
            <p class="slogan-text">
              We don't guess. We infer.<span class="blinking-cursor">_</span>
            </p>
          </div>

          <div class="feature-pills">
            <span class="pill">GPT-4.1</span>
            <span class="pill">GraphRAG</span>
            <span class="pill">text-embedding-3-large</span>
            <span class="pill">Multi-Agent</span>
          </div>
        </div>

        <div class="hero-right">
          <div class="hero-visual">
            <div class="visual-grid">
              <div class="grid-node" v-for="i in 12" :key="i" :style="{ animationDelay: (i * 0.15) + 's' }"></div>
            </div>
            <div class="visual-center">
              <div class="pulse-ring"></div>
              <div class="pulse-ring delay-1"></div>
              <div class="pulse-ring delay-2"></div>
              <span class="visual-icon">&#9670;</span>
            </div>
          </div>
        </div>
      </section>

      <section class="dashboard-section">
        <div class="left-panel">
          <div class="panel-header">
            <span class="status-dot">&#9632;</span> System Status
          </div>

          <h2 class="section-title">Ready</h2>
          <p class="section-desc">
            Prediction engine on standby. Upload unstructured data to initialize a simulation.
          </p>

          <div class="metrics-row">
            <div class="metric-card">
              <div class="metric-value">GPT-4.1</div>
              <div class="metric-label">Azure OpenAI LLM</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">3072d</div>
              <div class="metric-label">Embedding dimensions</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">GraphRAG</div>
              <div class="metric-label">Knowledge engine</div>
            </div>
          </div>

          <div class="steps-container">
            <div class="steps-header">
              <span class="diamond-icon">&#9671;</span> Workflow Sequence
            </div>
            <div class="workflow-list">
              <div v-for="(step, i) in steps" :key="i" class="workflow-item">
                <span class="step-num">{{ step.num }}</span>
                <div class="step-info">
                  <div class="step-title">{{ step.title }}</div>
                  <div class="step-desc">{{ step.desc }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="right-panel">
          <div class="console-box">
            <div class="console-section">
              <div class="console-header">
                <span>01 / Reality Seeds</span>
                <span>Supported: PDF, MD, TXT</span>
              </div>
              <div
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input ref="fileInput" type="file" multiple accept=".pdf,.md,.txt" @change="handleFileSelect" style="display: none" :disabled="loading" />
                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon-box">
                    <span class="upload-arrow">&#8593;</span>
                  </div>
                  <div class="upload-title">Drag & drop files here</div>
                  <div class="upload-hint">or click to browse</div>
                </div>
                <div v-else class="file-list">
                  <div v-for="(file, index) in files" :key="index" class="file-item">
                    <span class="file-icon">&#9724;</span>
                    <span class="file-name">{{ file.name }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn">&times;</button>
                  </div>
                </div>
              </div>
            </div>

            <div class="console-divider"><span>Parameters</span></div>

            <div class="console-section">
              <div class="console-header">
                <span>>_ 02 / Simulation Prompt</span>
              </div>
              <div class="input-wrapper">
                <textarea v-model="formData.simulationRequirement" class="code-input" placeholder="// Describe your simulation or prediction goal in natural language" rows="6" :disabled="loading"></textarea>
                <div class="model-badge">Engine: GPT-4.1 + GraphRAG</div>
              </div>
            </div>

            <div class="btn-section">
              <button class="start-engine-btn" @click="startSimulation" :disabled="!canSubmit || loading">
                <span v-if="!loading">Start Engine</span>
                <span v-else>Initializing...</span>
                <span class="btn-arrow">&#8594;</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <HistoryDatabase />
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'

const steps = [
  { num: '01', title: 'Graph Build', desc: 'Extract reality seeds from your document, build knowledge graph with Azure OpenAI GraphRAG' },
  { num: '02', title: 'Env Setup', desc: 'Generate agent personas, configure simulation parameters via GPT-4.1' },
  { num: '03', title: 'Simulation', desc: 'Run multi-agent simulation with dynamic memory updates and emergent behavior' },
  { num: '04', title: 'Report', desc: 'ReportAgent analyzes the simulation results and generates a detailed prediction report' },
  { num: '05', title: 'Interaction', desc: 'Chat with any agent from the simulated world or discuss findings with ReportAgent' },
]

const router = useRouter()

const formData = ref({ simulationRequirement: '' })
const files = ref([])
const loading = ref(false)
const error = ref('')
const isDragOver = ref(false)
const fileInput = ref(null)

const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== '' && files.value.length > 0
})

const triggerFileInput = () => { if (!loading.value) fileInput.value?.click() }
const handleFileSelect = (event) => { addFiles(Array.from(event.target.files)) }
const handleDragOver = () => { isDragOver.value = true }
const handleDragLeave = () => { isDragOver.value = false }
const handleDrop = (e) => { isDragOver.value = false; addFiles(Array.from(e.dataTransfer.files)) }

const addFiles = (newFiles) => {
  const allowed = ['.pdf', '.md', '.txt']
  const valid = newFiles.filter(f => allowed.some(ext => f.name.toLowerCase().endsWith(ext)))
  files.value = [...files.value, ...valid]
}

const removeFile = (index) => { files.value.splice(index, 1) }

const startSimulation = () => {
  if (!canSubmit.value || loading.value) return
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement)
    router.push({ name: 'Process', params: { projectId: 'new' } })
  })
}

</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.navbar {
  height: 64px;
  background: rgba(10, 14, 26, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-primary);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  letter-spacing: 2px;
  font-size: 1.1rem;
  color: var(--white);
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  color: var(--accent-blue);
  font-size: 1.2rem;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  padding: 3px 8px;
  border: 1px solid var(--border-secondary);
  border-radius: 4px;
  color: var(--text-muted);
}

.github-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: color 0.2s;
}

.github-link:hover {
  color: var(--accent-blue);
}

.arrow-icon {
  font-size: 0.9rem;
}

.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 60px 40px;
}

.hero-section {
  display: flex;
  justify-content: space-between;
  margin-bottom: 80px;
  position: relative;
}

.hero-left {
  flex: 1;
  padding-right: 60px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
}

.blue-tag {
  background: var(--accent-gradient);
  color: var(--white);
  padding: 5px 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
  font-size: 0.75rem;
  border-radius: 4px;
}

.version-text {
  color: var(--text-muted);
  font-weight: 500;
}

.main-title {
  font-size: 4rem;
  line-height: 1.15;
  font-weight: 700;
  margin: 0 0 40px 0;
  letter-spacing: -1.5px;
  color: var(--white);
}

.gradient-text {
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.hero-desc {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--text-secondary);
  max-width: 640px;
  margin-bottom: 40px;
}

.hero-desc p {
  margin-bottom: 1.5rem;
}

.highlight-white {
  color: var(--white);
  font-weight: 700;
}

.highlight-blue {
  color: var(--accent-blue);
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.highlight-code {
  background: var(--accent-glow);
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9em;
  color: var(--accent-cyan);
  font-weight: 600;
  border: 1px solid var(--border-primary);
}

.slogan-text {
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--text-primary);
  letter-spacing: 0.5px;
  border-left: 3px solid var(--accent-blue);
  padding-left: 15px;
  margin-top: 20px;
}

.blinking-cursor {
  color: var(--accent-blue);
  animation: blink 1s step-end infinite;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.feature-pills {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.pill {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  padding: 5px 12px;
  border: 1px solid var(--border-secondary);
  border-radius: 20px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
}

.hero-right {
  flex: 0.7;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-visual {
  width: 340px;
  height: 340px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.visual-grid {
  position: absolute;
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: repeat(3, 1fr);
  gap: 20px;
  opacity: 0.3;
}

.grid-node {
  width: 8px;
  height: 8px;
  background: var(--accent-blue);
  border-radius: 50%;
  justify-self: center;
  align-self: center;
  animation: nodeFloat 3s ease-in-out infinite;
}

@keyframes nodeFloat {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.5); opacity: 0.8; }
}

.visual-center {
  position: relative;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 1px solid var(--accent-blue);
  border-radius: 50%;
  animation: pulseRing 3s ease-out infinite;
}

.pulse-ring.delay-1 { animation-delay: 1s; }
.pulse-ring.delay-2 { animation-delay: 2s; }

@keyframes pulseRing {
  0% { transform: scale(1); opacity: 0.6; }
  100% { transform: scale(3); opacity: 0; }
}

.visual-icon {
  color: var(--accent-blue);
  font-size: 2rem;
  z-index: 1;
}

.dashboard-section {
  display: flex;
  gap: 40px;
  border-top: 1px solid var(--border-primary);
  padding-top: 60px;
  align-items: flex-start;
}

.left-panel {
  flex: 0.9;
}

.panel-header {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.status-dot {
  color: var(--accent-blue);
  font-size: 0.6rem;
}

.section-title {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 12px 0;
  color: var(--white);
}

.section-desc {
  color: var(--text-secondary);
  margin-bottom: 25px;
  line-height: 1.6;
  font-size: 0.95rem;
}

.metrics-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.metric-card {
  border: 1px solid var(--border-primary);
  padding: 18px 20px;
  min-width: 130px;
  background: var(--bg-card);
  border-radius: 8px;
  flex: 1;
}

.metric-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 4px;
  color: var(--white);
}

.metric-label {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.steps-container {
  border: 1px solid var(--border-primary);
  padding: 28px;
  background: var(--bg-card);
  border-radius: 8px;
}

.steps-header {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 25px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.diamond-icon {
  color: var(--accent-blue);
  font-size: 1rem;
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: var(--accent-blue);
  opacity: 0.5;
  font-size: 0.85rem;
  min-width: 24px;
}

.step-info {
  flex: 1;
}

.step-title {
  font-weight: 600;
  font-size: 0.95rem;
  margin-bottom: 3px;
  color: var(--text-primary);
}

.step-desc {
  font-size: 0.82rem;
  color: var(--text-muted);
  line-height: 1.5;
}

.right-panel {
  flex: 1.1;
}

.console-box {
  border: 1px solid var(--border-primary);
  background: var(--bg-card);
  border-radius: 10px;
  overflow: hidden;
}

.console-section {
  padding: 24px;
}

.console-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.upload-zone {
  border: 1px dashed var(--border-secondary);
  height: 200px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: var(--bg-secondary);
  border-radius: 8px;
  transition: all 0.3s;
}

.upload-zone.has-files {
  align-items: flex-start;
}

.upload-zone:hover,
.upload-zone.drag-over {
  background: var(--bg-tertiary);
  border-color: var(--accent-blue);
}

.upload-placeholder {
  text-align: center;
}

.upload-icon-box {
  width: 44px;
  height: 44px;
  border: 1px solid var(--border-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 14px;
  color: var(--accent-blue);
  border-radius: 8px;
  background: var(--bg-tertiary);
  font-size: 1.2rem;
}

.upload-arrow {
  font-family: sans-serif;
}

.upload-title {
  font-weight: 500;
  font-size: 0.9rem;
  margin-bottom: 4px;
  color: var(--text-primary);
}

.upload-hint {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.file-list {
  width: 100%;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  background: var(--bg-tertiary);
  padding: 10px 14px;
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.82rem;
}

.file-icon {
  color: var(--accent-blue);
  font-size: 0.6rem;
}

.file-name {
  flex: 1;
  margin: 0 12px;
  color: var(--text-primary);
}

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.3rem;
  color: var(--text-muted);
  transition: color 0.2s;
}

.remove-btn:hover {
  color: var(--danger);
}

.console-divider {
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.console-divider::before,
.console-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-primary);
}

.console-divider span {
  padding: 0 14px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: var(--text-muted);
  letter-spacing: 1px;
}

.input-wrapper {
  position: relative;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  border-radius: 8px;
  overflow: hidden;
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: 20px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.88rem;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 140px;
  color: var(--text-primary);
}

.code-input::placeholder {
  color: var(--text-muted);
}

.model-badge {
  position: absolute;
  bottom: 10px;
  right: 14px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: var(--text-muted);
}

.btn-section {
  padding: 0 24px 24px;
}

.start-engine-btn {
  width: 100%;
  background: var(--accent-gradient);
  color: var(--white);
  border: none;
  padding: 18px 24px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  letter-spacing: 1px;
  border-radius: 8px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.start-engine-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(59, 130, 246, 0.3);
}

.start-engine-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-engine-btn:disabled {
  background: var(--bg-tertiary);
  color: var(--text-muted);
  cursor: not-allowed;
  transform: none;
  border: 1px solid var(--border-primary);
}

.btn-arrow {
  font-size: 1.2rem;
}

@media (max-width: 1024px) {
  .dashboard-section {
    flex-direction: column;
  }
  .hero-section {
    flex-direction: column;
  }
  .hero-left {
    padding-right: 0;
    margin-bottom: 40px;
  }
  .hero-right {
    display: none;
  }
  .main-title {
    font-size: 2.8rem;
  }
}

</style>
