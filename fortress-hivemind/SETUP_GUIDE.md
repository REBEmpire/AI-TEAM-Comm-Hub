# Fortress HiveMind Setup Guide

This guide helps you set up the **Fortress HiveMind** using Eigent-AI, LiteLLM, and a custom MCP Server.

## Prerequisites
- Docker & Docker Compose
- Python 3.10+ and `uv` (recommended) or `pip`
- Eigent-AI Desktop App installed
- API Keys for Anthropic, Gemini, xAI (Grok)

## 1. Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and add your API keys.

## 2. Start the Gateway (LiteLLM)

Run the LiteLLM proxy which unifies all your AI providers:

```bash
docker-compose up -d
```

- **LiteLLM UI:** http://localhost:4000/ui
- **API Endpoint:** http://localhost:4000

## 3. Register the MCP Server in Eigent

1. Open Eigent-AI.
2. Go to **Settings > MCP & Tools**.
3. Locate the configuration file editor (usually `config.json` for MCP).
4. Add the entry from `eigent_config_snippet.json`.
   - **IMPORTANT:** Replace `/YOUR/PATH/TO/...` with the actual absolute path to this `fortress-hivemind` directory on your machine.
   - Ensure `uv` is in your system PATH, or provide the full path to the `uv` executable.

## 4. Create Agents in Eigent

Create "Workers" in Eigent using the System Prompts provided in `config/agents/`:

### Agent 1: Claude (Senior Analyst)
- **Model:** Select `claude-analyst` (mapped via LiteLLM) or use standard Claude if you prefer direct key.
- **System Prompt:** Copy content from `config/agents/claude_analyst_prompt.md`.

### Agent 2: Gemini (Research Lead)
- **Model:** Select `gemini-researcher`.
- **System Prompt:** Copy content from `config/agents/gemini_researcher_prompt.md`.

### Agent 3: Abacus (Compute Interface)
- **Model:** Select `abacus-driver` (this is a lightweight model like GPT-4o-mini).
- **System Prompt:** Copy content from `config/agents/abacus_driver_prompt.md`.
- **Note:** This agent uses the `create_github_task` tool to "talk" to the real Abacus system via the file system.

## 5. Using the System

- **Talking to Agents:** Chat with Claude or Gemini directly in Eigent.
- **Delegating to Abacus:** Ask the "Abacus" agent to perform a calculation. It will create a file in `hivemind-comms/abacus-compute/inbox/`.
- **Simulating Abacus Response:**
  - Since we don't have the real Abacus backend running here, you can simulate a response by creating a file in `hivemind-comms/abacus-compute/outbox/{job_id}_response.md`.
  - The Abacus agent will then be able to read it using the `read_response` tool.

## Directory Structure
- `litellm/`: Configuration for the API Gateway.
- `src/`: Source code for the MCP Server.
- `hivemind-comms/`: The "filesystem bus" where agents exchange messages/tasks.
- `artifacts/`: Where agents store permanent outputs.
