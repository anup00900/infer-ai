<div align="center">

# INFER

### We don't guess. We infer.

[![GPT-4.1](https://img.shields.io/badge/LLM-GPT--4.1-blue?style=for-the-badge&logo=openai&logoColor=white)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
[![GraphRAG](https://img.shields.io/badge/Knowledge-GraphRAG-0ea5e9?style=for-the-badge&logo=microsoftazure&logoColor=white)](https://github.com/microsoft/graphrag)
[![Embeddings](https://img.shields.io/badge/Embeddings-3072d-06b6d4?style=for-the-badge&logo=openai&logoColor=white)](https://platform.openai.com/docs/guides/embeddings)
[![Vue 3](https://img.shields.io/badge/Frontend-Vue%203-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![Python](https://img.shields.io/badge/Backend-Python%203.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Upload any document. Simulate the future. Predict what happens next.**

*Multi-Agent Prediction Engine*

*A multi-agent swarm intelligence engine that simulates public opinion, market sentiment, and social dynamics using GPT-4.1 and in-memory GraphRAG.*

---

</div>

## What is Infer?

Infer is an **enterprise-grade multi-agent prediction engine**. Upload any document -- a press release, policy draft, financial report, or news article -- and it generates hundreds of AI agents with unique personalities that simulate real-world reactions on social media platforms. Posts, arguments, opinion shifts, sentiment cascades -- all predicted hour by hour.

```
Document  -->  Knowledge Graph  -->  Agent Personas  -->  Simulation  -->  Prediction Report
  (PDF)        (GraphRAG)           (GPT-4.1)           (Multi-Agent)     (Analysis + Chat)
```

---

## Architecture

```
                    +------------------------------------------+
                    |             Infer Frontend                |
                    |     Vue 3 + D3.js + Dark Premium UI      |
                    +-------------------+----------------------+
                                        |
                                   REST API
                                        |
                    +-------------------v----------------------+
                    |           Flask API Layer                 |
                    |   graph.py | simulation.py | report.py   |
                    +-------------------+----------------------+
                                        |
                    +-------------------v----------------------+
                    |           Service Layer                   |
                    |  EntityReader   GraphToolsService         |
                    |  GraphMemoryUpdater   ReportAgent         |
                    +-------------------+----------------------+
                                        |
              +-------------------------+-------------------------+
              |                                                   |
   +----------v-----------+                          +-----------v-----------+
   |   In-Memory GraphRAG  |                          |    Azure OpenAI       |
   |  +------------------+ |                          |  +------------------+ |
   |  | Vector Search    | |                          |  | GPT-4.1 (LLM)   | |
   |  | Hybrid BM25      | |                          |  | text-embed-3-lg  | |
   |  | JSON Persistence | |                          |  | 3072 dimensions  | |
   |  +------------------+ |                          |  +------------------+ |
   +-----------------------+                          +-----------------------+
```

---

## Key Innovations vs Original

This project is a **complete reimagining** of the original Chinese-language MiroFish simulation engine. Here's what changed:

| Feature | Original (Chinese) | **Infer** |
|---|---|---|
| **Language** | Chinese UI (1000+ strings) | **Full English UI** |
| **LLM** | Ollama / qwen2.5 (local) | **Azure OpenAI GPT-4.1** |
| **Embeddings** | nomic-embed-text (768d, local) | **text-embedding-3-large (3072d)** |
| **Graph Database** | Neo4j Community Edition | **In-Memory GraphRAG (zero dependencies)** |
| **Setup Complexity** | Docker + Neo4j + Ollama + GPU | **Single `pip install` + API key** |
| **Hardware Required** | 16GB RAM + 10GB VRAM minimum | **Any machine with internet** |
| **UI Theme** | White/light theme | **Premium dark blue/black theme** |
| **Cloud Dependencies** | None (fully local) | **Azure OpenAI (superior quality)** |
| **Vector Search** | Neo4j vector indexes | **Numpy cosine similarity + BM25 hybrid** |
| **Data Persistence** | Neo4j database files | **JSON file persistence** |
| **Knowledge Extraction** | Basic NER via Ollama | **Advanced NER/RE via GPT-4.1** |

### What's New

- **Zero-Infrastructure Setup** -- No Docker, no Neo4j, no GPU required. Just Python + Node.js + an API key.
- **4x Better Embeddings** -- text-embedding-3-large produces 3072-dimensional vectors vs the original 768d, capturing far more semantic nuance.
- **GPT-4.1 Intelligence** -- Every agent persona, every simulation step, every report is powered by state-of-the-art GPT-4.1 instead of local quantized models.
- **In-Memory GraphRAG** -- The knowledge graph runs entirely in memory with hybrid vector + keyword search. No external database means no connection issues, no schema migrations, no port conflicts.
- **Premium Dark UI** -- A completely redesigned interface with a professional dark blue/black aesthetic, animated elements, and modern typography.

---

## Workflow

```
1. GRAPH BUILD       Extract entities & relationships from your document.
                     Build a knowledge graph with Azure OpenAI GraphRAG.

2. ENV SETUP         Generate hundreds of agent personas with unique
                     personalities, opinions, influence levels, and memory.

3. SIMULATION        Agents interact on simulated social platforms:
                     posting, replying, arguing, shifting opinions.
                     Sentiment tracked in real-time.

4. REPORT            ReportAgent analyzes post-simulation data,
                     interviews focus groups, searches the knowledge
                     graph, and generates structured analysis.

5. INTERACTION       Chat with any agent from the simulated world.
                     Ask them why they said what they said.
                     Full memory and personality persists.
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Azure OpenAI API key (or any OpenAI-compatible endpoint)

### Installation

```bash
# Clone the repository
git clone https://github.com/anuproy/infer.git
cd infer

# Configure your API key
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install

# Start the backend
cd ../backend
python run.py

# In another terminal, start the frontend
cd frontend
npm run dev
```

Open `http://localhost:3000` -- that's it.

### Configuration

All settings are in `.env`:

```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1

# Embeddings
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=3072

# Graph Storage (in-memory, no external DB needed)
GRAPH_STORAGE_TYPE=memory
GRAPH_DATA_DIR=./data/graphs
```

---

## Use Cases

| Use Case | Description |
|---|---|
| **PR Crisis Testing** | Simulate public reaction to a press release before publishing |
| **Trading Signals** | Feed financial news, observe simulated market sentiment shifts |
| **Policy Impact** | Test draft regulations against simulated public response |
| **Competitive Analysis** | Model how markets react to competitor announcements |
| **Product Launch** | Predict social media response to product announcements |
| **Risk Assessment** | Simulate cascading effects of organizational decisions |

---

## Tech Stack

| Component | Technology |
|---|---|
| **LLM** | Azure OpenAI GPT-4.1 |
| **Embeddings** | text-embedding-3-large (3072d) |
| **Knowledge Graph** | In-Memory GraphRAG with JSON persistence |
| **Search** | Hybrid: 0.7x vector cosine + 0.3x BM25 keyword |
| **Backend** | Python 3.11+ / Flask |
| **Frontend** | Vue 3 + D3.js + Vite |
| **Simulation** | OASIS (CAMEL-AI) multi-agent framework |
| **NER/RE** | GPT-4.1 structured extraction |

---

## Project Structure

```
infer/
  backend/
    app/
      api/           # Flask REST API endpoints
      models/        # Data models (Project, Task)
      services/      # Business logic (simulation, reports)
      storage/       # GraphRAG storage layer
      utils/         # LLM client, logger, file parser
    run.py           # Backend entry point
  frontend/
    src/
      api/           # Axios API client
      components/    # Vue step components
      views/         # Page views (Home, Process, Report)
      router/        # Vue Router config
    index.html       # Entry HTML
  .env.example       # Configuration template
  docker-compose.yml # Docker setup (optional)
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built by Anup Roy**

*INFER -- We don't guess. We infer.*

</div>
