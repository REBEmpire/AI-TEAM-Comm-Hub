# FORTRESS HIVEMIND: Founding Build Prompt
## For Claude Code Planning Mode - Broad Perspective R&D

---

## PROJECT OVERVIEW

**Project Name:** Fortress HiveMind  
**Organization:** Broad Perspective R&D (BPR&D)  
**Objective:** Build a multi-AI orchestration system that enables autonomous AI "employees" to communicate, collaborate, and complete tasks while providing human oversight through a unified dashboard.

**Core Problem:** We have multiple AI subscriptions (Claude, Gemini, Grok, Abacus) operating as autonomous workers, but they cannot communicate with each other or report status to a central location.

**Solution:** Fork `agent-service-toolkit`, extend it with multi-provider adapters, add an Access Layer for API/GitHub fallback communication, and enhance the dashboard for full visibility.

---

## TECHNICAL FOUNDATION

### Starting Point
**Repository to Fork:** `https://github.com/JoshuaC215/agent-service-toolkit`

This provides:
- LangGraph-based agent orchestration
- FastAPI backend with streaming endpoints
- Streamlit dashboard
- PostgreSQL persistence
- Docker Compose setup
- Human-in-the-loop capability

### What We're Adding
1. **Multi-Provider Adapters** - Claude, Gemini, Grok, Abacus
2. **Access Layer** - Handles API calls with GitHub fallback for non-API agents
3. **Enhanced Dashboard** - Command center, message stream, escalation queue, analytics
4. **Unified Job Protocol (UJP)** - Standardized JSON schema for all agent communication
5. **Governance Controls** - Policy engine, approval gates, audit logging
6. **Artifact Storage** - Immutable outputs with checksums in PostgreSQL

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                     STREAMLIT DASHBOARD                          │
│  [Command Center] [Message Feed] [Escalations] [Analytics]      │
└───────────────────────────────┬─────────────────────────────────┘
                                │ WebSocket
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI ORCHESTRATOR                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Task Router │  │ Redis Bus   │  │ Context Mgr │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────────────────────────────────────────┐            │
│  │              LANGGRAPH STATE MACHINE            │            │
│  └─────────────────────────────────────────────────┘            │
│                                                                  │
│  ┌─────────────────────────────────────────────────┐            │
│  │              ACCESS LAYER (Per Provider)         │            │
│  │   [API Primary] ──failed──► [GitHub Fallback]   │            │
│  └─────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Claude    │ │   Gemini    │ │    Grok     │ │   Abacus    │
│   Adapter   │ │   Adapter   │ │   Adapter   │ │   Adapter   │
│  [API+GH]   │ │  [API+GH]   │ │  [API+GH]   │ │  [API+GH]   │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

---

## ACCESS LAYER SPECIFICATION

### Purpose
Handle the reality that not all AI providers have API access ready. Provides seamless fallback to GitHub-based async communication.

### Access Matrix (Current State)

| Provider | API Ready | Auth Type | GitHub Fallback | Primary Use |
|----------|-----------|-----------|-----------------|-------------|
| Claude | ✅ Yes | API Key | Backup | Analysis, synthesis, code review |
| Gemini | ✅ Yes | API Key/OAuth | Backup | Research, Google Workspace |
| Grok | ✅ Yes | API Key | Backup | Real-time data, fact-checking |
| Abacus | ⚠️ TBD | API Key | Primary initially | Deep computation, modeling |

### GitHub Fallback Protocol

When API is unavailable or fails:

1. **Orchestrator creates instruction file:**
   ```
   /hivemind-comms/{agent_name}/inbox/{job_id}.md
   ```

2. **File contains:**
   ```markdown
   # Job: {job_id}
   **From:** orchestrator
   **To:** {agent_name}
   **Priority:** {high|normal|low}
   **Created:** {ISO timestamp}
   **Deadline:** {ISO timestamp or "async"}
   
   ## Task
   {Detailed task description}
   
   ## Context
   {Relevant background, links to artifacts}
   
   ## Expected Output
   {What format/structure is expected}
   
   ## Respond To
   Comment on this file or create: /hivemind-comms/{agent_name}/outbox/{job_id}_response.md
   ```

3. **Agent (via human relay or automation) processes and responds**

4. **Orchestrator polls for responses or receives webhook notification**

### Adapter Interface (All Providers)

```python
from abc import ABC, abstractmethod
from typing import Optional
from enum import Enum

class AccessMethod(Enum):
    API = "api"
    GITHUB = "github"
    HYBRID = "hybrid"  # Try API, fall back to GitHub

class BaseAdapter(ABC):
    """Base class for all AI provider adapters."""
    
    provider_name: str
    access_method: AccessMethod
    api_available: bool
    github_repo: str = "BPR-D/hivemind-comms"
    
    @abstractmethod
    async def invoke(self, job: JobMessage) -> JobResponse:
        """Send job to AI provider, returns response."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Verify provider is accessible."""
        pass
    
    async def invoke_with_fallback(self, job: JobMessage) -> JobResponse:
        """Try API first, fall back to GitHub if needed."""
        if self.api_available:
            try:
                return await self.invoke(job)
            except Exception as e:
                logger.warning(f"{self.provider_name} API failed: {e}, falling back to GitHub")
        
        return await self.invoke_via_github(job)
    
    async def invoke_via_github(self, job: JobMessage) -> JobResponse:
        """Create instruction file in GitHub repo, await response."""
        # Create inbox file
        file_path = f"hivemind-comms/{self.provider_name}/inbox/{job.job_id}.md"
        content = self._format_github_instruction(job)
        await self.github_client.create_file(file_path, content)
        
        # Poll for response (or await webhook)
        return await self._await_github_response(job.job_id)
```

---

## UNIFIED JOB PROTOCOL (UJP)

### Job Message Schema

```json
{
  "job_id": "uuid-v4",
  "version": "1.0",
  "created_at": "2026-01-27T15:30:00Z",
  "deadline": "2026-01-27T16:00:00Z",
  
  "routing": {
    "from_agent": "orchestrator",
    "to_agent": "claude-analyst",
    "thread_id": "project-alpha-001",
    "priority": "high",
    "requires_approval": false
  },
  
  "task": {
    "type": "analysis",
    "title": "Review Q4 financial projections",
    "description": "Analyze the attached spreadsheet...",
    "inputs": {
      "documents": ["artifact:abc123"],
      "context": "Previous analysis found..."
    },
    "expected_output": {
      "format": "markdown",
      "sections": ["summary", "findings", "recommendations"]
    }
  },
  
  "constraints": {
    "max_tokens": 4000,
    "budget_usd": 0.50,
    "timeout_seconds": 300
  },
  
  "metadata": {
    "created_by": "human:russell",
    "tags": ["finance", "q4", "projections"],
    "parent_job": null
  }
}
```

### Job Response Schema

```json
{
  "job_id": "uuid-v4",
  "response_id": "uuid-v4",
  "created_at": "2026-01-27T15:35:00Z",
  
  "status": "completed",
  "status_detail": null,
  
  "result": {
    "content": "## Summary\n...",
    "format": "markdown",
    "artifacts": [
      {
        "artifact_id": "def456",
        "type": "document",
        "checksum": "sha256:...",
        "storage_path": "artifacts/def456.md"
      }
    ]
  },
  
  "metrics": {
    "tokens_input": 1200,
    "tokens_output": 850,
    "cost_usd": 0.032,
    "latency_ms": 4500,
    "model_used": "claude-sonnet-4-5-20250929"
  },
  
  "follow_up": {
    "needs_human": false,
    "needs_agent": "gemini-researcher",
    "request": "Need current market data to validate projections"
  }
}
```

---

## AGENT CONFIGURATIONS

### Agent Registry Schema

```yaml
# config/agents/claude-analyst.yaml
agent_id: claude-analyst
display_name: "Claude (Senior Analyst)"
provider: anthropic
enabled: true

access:
  method: hybrid  # api with github fallback
  api_key_env: ANTHROPIC_API_KEY
  github_path: claude-analyst

model:
  name: claude-sonnet-4-5-20250929
  max_tokens: 8192
  temperature: 0.7

capabilities:
  - document_analysis
  - code_review
  - long_context_synthesis
  - structured_reasoning
  
specialties:
  primary:
    - "Complex multi-document analysis"
    - "Technical writing and reports"
    - "Code explanation and review"
  secondary:
    - "Research synthesis"
    - "Data interpretation"

routing:
  task_affinities:
    analysis: 1.0      # Best choice
    synthesis: 0.9
    code_review: 0.9
    research: 0.5      # Can do, not optimal
    real_time: 0.0     # Cannot do

limits:
  daily_budget_usd: 50.00
  max_concurrent: 5
  timeout_seconds: 300

system_prompt: |
  You are Claude, a senior analyst at Broad Perspective R&D.
  
  ## Your Role
  You excel at deep analysis, document review, code explanation, and synthesizing 
  complex information into clear recommendations.
  
  ## Team Communication
  When you need help from teammates, include in your response:
  
  TEAMMATE_REQUEST:
  - agent: {agent_id}
  - task: {what you need}
  - context: {relevant background}
  - priority: {high|normal|low}
  
  ## Available Teammates
  - gemini-researcher: Web search, Google Workspace, large document processing
  - grok-intel: Real-time data, social trends, fact-checking, devil's advocate
  - abacus-compute: Heavy computation, predictive modeling, data processing
  
  ## Escalation
  If you need human input:
  
  HUMAN_ESCALATION:
  - reason: {why human needed}
  - question: {specific question}
  - options: {choices if applicable}
  - deadline: {when you need answer}
  
  ## Output Standards
  - Always cite sources and explain reasoning
  - Flag uncertainty explicitly
  - Provide confidence levels for conclusions
  - Structure outputs for easy scanning
```

### Additional Agent Configs

```yaml
# config/agents/gemini-researcher.yaml
agent_id: gemini-researcher
display_name: "Gemini (Research Lead)"
provider: google
model:
  name: gemini-2.0-pro
specialties:
  primary:
    - "Web research and current events"
    - "Google Workspace integration"
    - "Large document summarization"
routing:
  task_affinities:
    research: 1.0
    real_time: 0.8
    synthesis: 0.7

---
# config/agents/grok-intel.yaml
agent_id: grok-intel
display_name: "Grok (Intelligence Analyst)"
provider: xai
model:
  name: grok-3
specialties:
  primary:
    - "Real-time information retrieval"
    - "Social media intelligence"
    - "Contrarian analysis / devil's advocate"
routing:
  task_affinities:
    real_time: 1.0
    fact_check: 0.9
    research: 0.7

---
# config/agents/abacus-compute.yaml
agent_id: abacus-compute
display_name: "Abacus (Computation Engine)"
provider: abacus
access:
  method: github  # Primary via GitHub until API confirmed
model:
  name: deep-agent
specialties:
  primary:
    - "Complex calculations"
    - "Predictive modeling"
    - "Data pipeline processing"
routing:
  task_affinities:
    computation: 1.0
    modeling: 0.9
    analysis: 0.6
```

---

## DATABASE SCHEMA

### Core Tables

```sql
-- PostgreSQL schema for Fortress HiveMind

-- Agents registry
CREATE TABLE agents (
    agent_id VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    config JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Jobs (using UJP schema)
CREATE TABLE jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(10) DEFAULT '1.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deadline TIMESTAMPTZ,
    
    -- Routing
    from_agent VARCHAR(50),
    to_agent VARCHAR(50) REFERENCES agents(agent_id),
    thread_id VARCHAR(100),
    priority VARCHAR(10) DEFAULT 'normal',
    requires_approval BOOLEAN DEFAULT false,
    
    -- Task
    task_type VARCHAR(50),
    title VARCHAR(200),
    description TEXT,
    inputs JSONB,
    expected_output JSONB,
    
    -- Constraints
    max_tokens INTEGER,
    budget_usd DECIMAL(10, 4),
    timeout_seconds INTEGER,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    status_detail TEXT,
    
    -- Metadata
    created_by VARCHAR(100),
    tags TEXT[],
    parent_job UUID REFERENCES jobs(job_id),
    
    -- Indexes
    CONSTRAINT valid_status CHECK (status IN ('pending', 'assigned', 'in_progress', 'completed', 'failed', 'escalated', 'cancelled'))
);

-- Job responses
CREATE TABLE job_responses (
    response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(job_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Result
    status VARCHAR(20) NOT NULL,
    content TEXT,
    format VARCHAR(20),
    
    -- Metrics
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd DECIMAL(10, 6),
    latency_ms INTEGER,
    model_used VARCHAR(100),
    
    -- Follow-up
    needs_human BOOLEAN DEFAULT false,
    needs_agent VARCHAR(50),
    follow_up_request TEXT
);

-- Artifacts (immutable outputs)
CREATE TABLE artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(job_id),
    response_id UUID REFERENCES job_responses(response_id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    artifact_type VARCHAR(50),
    filename VARCHAR(255),
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    checksum VARCHAR(100) NOT NULL,  -- sha256:...
    storage_path TEXT NOT NULL,
    
    metadata JSONB
);

-- Human escalations
CREATE TABLE escalations (
    escalation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(job_id),
    response_id UUID REFERENCES job_responses(response_id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    reason TEXT NOT NULL,
    question TEXT,
    options JSONB,
    deadline TIMESTAMPTZ,
    
    status VARCHAR(20) DEFAULT 'pending',
    human_response TEXT,
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(100)
);

-- Message log (all inter-agent communication)
CREATE TABLE message_log (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(job_id),
    thread_id VARCHAR(100),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    from_agent VARCHAR(50),
    to_agent VARCHAR(50),
    message_type VARCHAR(20),
    
    content JSONB NOT NULL,
    
    -- For audit
    access_method VARCHAR(20),  -- 'api' or 'github'
    raw_request JSONB,
    raw_response JSONB
);

-- Cost tracking
CREATE TABLE cost_ledger (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(50) REFERENCES agents(agent_id),
    job_id UUID REFERENCES jobs(job_id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_usd DECIMAL(10, 6),
    
    daily_total DECIMAL(10, 4),  -- Running total for budget checks
    monthly_total DECIMAL(10, 4)
);

-- Indexes for common queries
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_thread ON jobs(thread_id);
CREATE INDEX idx_jobs_to_agent ON jobs(to_agent);
CREATE INDEX idx_jobs_created ON jobs(created_at DESC);
CREATE INDEX idx_escalations_pending ON escalations(status) WHERE status = 'pending';
CREATE INDEX idx_messages_thread ON message_log(thread_id);
CREATE INDEX idx_messages_created ON message_log(created_at DESC);
CREATE INDEX idx_costs_agent_date ON cost_ledger(agent_id, created_at);
```

---

## DASHBOARD SPECIFICATIONS

### Views Required

#### 1. Command Center (Home)
- **Agent Status Cards**: For each agent show: name, status (idle/busy/error), current job, queue depth
- **Active Jobs Grid**: Table of in-progress jobs with progress indicators
- **Quick Actions**: Create job, pause all, view escalations
- **System Health**: API status per provider, Redis connection, DB status

#### 2. Message Stream
- **Real-time Feed**: Chronological list of all agent communications
- **Filters**: By agent, thread, job, time range, message type
- **Expandable Details**: Click to see full message content, request/response
- **Search**: Full-text search across messages

#### 3. Escalation Queue
- **Pending Items**: Cards showing what needs human attention
- **Context Display**: Show relevant job history and agent reasoning
- **Response Input**: Text field + quick action buttons
- **Bulk Actions**: Approve all, reassign, dismiss

#### 4. Analytics
- **Cost Dashboard**: Spend by agent, by day, by job type; budget remaining
- **Performance**: Latency trends, success rates, token efficiency
- **Usage Patterns**: Jobs by type, peak hours, agent utilization

#### 5. Job Management
- **Create Job**: Form to specify task, assign agent, set constraints
- **Job History**: Searchable archive of all jobs
- **Job Detail**: Full view of job lifecycle, messages, artifacts

---

## IMPLEMENTATION PHASES

### Phase 0: Foundation (Days 1-2)
**Goal:** Running baseline with one agent

- [ ] Fork `agent-service-toolkit` to `BPR-D/fortress-hivemind`
- [ ] Set up local development environment
- [ ] Configure PostgreSQL with schema above
- [ ] Configure Redis
- [ ] Create `.env` with available API keys
- [ ] Verify Claude adapter works (toolkit may have OpenAI default)
- [ ] Test basic job submission and response
- [ ] Verify Streamlit dashboard connects

**Success Criteria:** Can submit job to Claude via dashboard, see response

### Phase 1: Multi-Provider (Days 3-7)
**Goal:** All four AI systems accessible

- [ ] Create adapter base class with fallback logic
- [ ] Implement Gemini adapter (API)
- [ ] Implement Grok adapter (API)
- [ ] Implement Abacus adapter (GitHub fallback)
- [ ] Create GitHub communication module
- [ ] Set up `hivemind-comms` repository structure
- [ ] Test each adapter independently
- [ ] Test fallback mechanism

**Success Criteria:** All four agents respond to jobs (API or GitHub)

### Phase 2: Orchestration (Week 2)
**Goal:** Agents can collaborate

- [ ] Implement UJP message parsing
- [ ] Build task router with affinity scoring
- [ ] Implement `TEAMMATE_REQUEST` detection and routing
- [ ] Implement `HUMAN_ESCALATION` detection and queuing
- [ ] Add thread context management
- [ ] Build agent-to-agent handoff workflow in LangGraph
- [ ] Test multi-agent task completion

**Success Criteria:** Job assigned to Claude can request Gemini's help, receive it, continue

### Phase 3: Dashboard Enhancement (Week 3)
**Goal:** Full visibility and control

- [ ] Build Command Center view
- [ ] Build Message Stream with real-time updates
- [ ] Build Escalation Queue with response interface
- [ ] Build Analytics dashboard
- [ ] Build Job Management views
- [ ] Add WebSocket for real-time updates
- [ ] Add cost tracking and budget alerts

**Success Criteria:** Dashboard shows all activity, can respond to escalations

### Phase 4: Hardening (Week 4)
**Goal:** Production-ready

- [ ] Add comprehensive error handling
- [ ] Implement retry logic with backoff
- [ ] Add rate limiting per agent
- [ ] Implement governance/approval gates
- [ ] Add audit logging
- [ ] Write deployment documentation
- [ ] Create backup/restore procedures
- [ ] Load testing

**Success Criteria:** System handles failures gracefully, costs are controlled

---

## FILE STRUCTURE

```
fortress-hivemind/
├── src/
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py              # BaseAdapter class
│   │   ├── claude_adapter.py
│   │   ├── gemini_adapter.py
│   │   ├── grok_adapter.py
│   │   ├── abacus_adapter.py
│   │   └── github_fallback.py   # GitHub communication module
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── router.py            # Task routing logic
│   │   ├── context.py           # Thread context management
│   │   ├── governance.py        # Approval gates, policies
│   │   └── workflows/           # LangGraph workflow definitions
│   │       ├── single_agent.py
│   │       ├── multi_agent.py
│   │       └── human_loop.py
│   │
│   ├── protocol/
│   │   ├── __init__.py
│   │   ├── ujp.py               # Unified Job Protocol schemas
│   │   ├── messages.py          # Message type definitions
│   │   └── validation.py        # Schema validation
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py          # PostgreSQL operations
│   │   ├── artifacts.py         # Artifact storage with checksums
│   │   └── cache.py             # Redis operations
│   │
│   ├── dashboard/
│   │   ├── app.py               # Main Streamlit app
│   │   ├── pages/
│   │   │   ├── command_center.py
│   │   │   ├── message_stream.py
│   │   │   ├── escalations.py
│   │   │   ├── analytics.py
│   │   │   └── job_management.py
│   │   └── components/
│   │       ├── agent_card.py
│   │       ├── job_card.py
│   │       └── message_item.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── routes/
│   │   │   ├── jobs.py
│   │   │   ├── agents.py
│   │   │   ├── messages.py
│   │   │   ├── escalations.py
│   │   │   └── analytics.py
│   │   └── websocket.py         # Real-time updates
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py
│       ├── metrics.py
│       └── costs.py
│
├── config/
│   ├── agents/
│   │   ├── claude-analyst.yaml
│   │   ├── gemini-researcher.yaml
│   │   ├── grok-intel.yaml
│   │   └── abacus-compute.yaml
│   ├── settings.py              # Pydantic settings
│   └── prompts/                 # System prompt templates
│
├── migrations/
│   └── 001_initial_schema.sql
│
├── tests/
│   ├── adapters/
│   ├── orchestrator/
│   ├── protocol/
│   └── integration/
│
├── docker-compose.yaml
├── Dockerfile
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## ENVIRONMENT VARIABLES

```bash
# .env.example

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
GROK_API_KEY=xai-...
ABACUS_API_KEY=...  # Leave empty if using GitHub fallback

# GitHub (for fallback communication)
GITHUB_TOKEN=ghp_...
GITHUB_REPO=BPR-D/hivemind-comms

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/hivemind

# Redis
REDIS_URL=redis://localhost:6379

# Application
APP_ENV=development
LOG_LEVEL=INFO
DASHBOARD_PORT=8501
API_PORT=8080

# Cost Controls
DAILY_BUDGET_TOTAL_USD=200
ALERT_THRESHOLD_PCT=80
```

---

## SUCCESS METRICS

| Metric | Target | Measurement |
|--------|--------|-------------|
| Job completion rate | >90% | Jobs completed / Jobs created |
| Agent handoff success | >95% | Successful handoffs / Handoff attempts |
| Escalation response time | <1 hour | Time from escalation to human response |
| API uptime per provider | >99% | Successful calls / Total calls |
| Cost per job | Track baseline | Total cost / Jobs completed |
| Dashboard latency | <500ms | Time to load any view |

---

## FIRST TASK FOR THE SYSTEM

Once Phase 1 is complete, run this test job:

```json
{
  "task": {
    "type": "research_and_analysis",
    "title": "Evaluate Fortress HiveMind Architecture",
    "description": "As our first collaborative task, I want each agent to review the Fortress HiveMind architecture and provide feedback from their specialty perspective.",
    "inputs": {
      "documents": ["This founding prompt document"]
    },
    "expected_output": {
      "format": "markdown",
      "sections": ["strengths", "weaknesses", "recommendations"]
    }
  },
  "routing": {
    "workflow": "parallel_then_synthesize",
    "agents": ["claude-analyst", "gemini-researcher", "grok-intel", "abacus-compute"],
    "synthesizer": "claude-analyst"
  }
}
```

This will validate:
- All agents can receive and process jobs
- Inter-agent communication works
- Synthesis/handoff workflow functions
- Dashboard shows the full process

---

## NOTES FOR CLAUDE CODE

1. **Start with the fork** - Don't build from scratch. The toolkit gives us 60-70% of what we need.

2. **Adapters first** - Get all four providers responding before building fancy features.

3. **GitHub fallback is real** - Some agents may only work via GitHub initially. Build this path properly.

4. **UJP is the contract** - All communication follows the Unified Job Protocol. No exceptions.

5. **Test incrementally** - Each phase should end with working functionality, not half-built features.

6. **Cost tracking from day 1** - Log every API call's cost. Surprises are expensive.

7. **The dashboard is the product** - If Russell can't see it in the dashboard, it doesn't exist.

---

*This prompt represents the synthesized wisdom of Claude, Gemini, GPT-5.2, and Grok, plus extensive open-source research. The architecture is validated, the path is clear.*

*Build the fortress. Unleash the hive mind.*

---

**Document Version:** 1.0  
**Created:** January 27, 2026  
**Author:** Claude (with contributions from the BPR&D AI team)  
**For:** Russell Teter, Broad Perspective R&D
