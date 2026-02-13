import os
import glob
import time
import json
from pathlib import Path
from typing import Optional, List
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

# Initialize FastMCP server
mcp = FastMCP("Fortress HiveMind Access Layer")

# Configuration
# Resolves to the 'fortress-hivemind' root directory (parent of 'src')
ROOT_DIR = Path(os.getenv("HIVEMIND_ROOT", Path(__file__).parent.parent.resolve()))
COMMS_DIR = ROOT_DIR / "hivemind-comms"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"

# Ensure directories exist
COMMS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

class AgentStatus(BaseModel):
    name: str
    inbox_count: int
    outbox_count: int

@mcp.tool()
def list_agents() -> List[str]:
    """List all agents configured in the communication directory."""
    return [d.name for d in COMMS_DIR.iterdir() if d.is_dir()]

@mcp.tool()
def register_agent(agent_name: str) -> str:
    """Register a new agent (creates inbox/outbox directories)."""
    agent_path = COMMS_DIR / agent_name
    (agent_path / "inbox").mkdir(parents=True, exist_ok=True)
    (agent_path / "outbox").mkdir(parents=True, exist_ok=True)
    return f"Agent {agent_name} registered at {agent_path}"

@mcp.tool()
def create_github_task(agent_name: str, job_id: str, content: str, priority: str = "normal") -> str:
    """
    Create a task file for an agent that uses GitHub fallback (e.g., Abacus).

    Args:
        agent_name: Name of the target agent (e.g., 'abacus-compute')
        job_id: Unique ID for the job
        content: The instructions for the agent
        priority: Priority level (high, normal, low)
    """
    agent_dir = COMMS_DIR / agent_name / "inbox"
    if not agent_dir.exists():
        return f"Error: Agent {agent_name} not found. Register it first."

    filename = f"{job_id}.md"
    file_path = agent_dir / filename

    header = f"""---
job_id: {job_id}
from: orchestrator
priority: {priority}
created_at: {time.time()}
---

"""
    with file_path.open("w") as f:
        f.write(header)
        f.write(content)
    return f"Task created at {file_path}"

@mcp.tool()
def read_response(agent_name: str, job_id: str) -> str:
    """
    Read the response file from an agent.

    Args:
        agent_name: Name of the agent
        job_id: The job ID to check for
    """
    outbox_dir = COMMS_DIR / agent_name / "outbox"
    # Look for files matching job_id_response.md or similar
    # We'll just look for standard pattern: {job_id}_response.md
    expected_file = outbox_dir / f"{job_id}_response.md"

    if expected_file.exists():
        return expected_file.read_text()

    return "PENDING: No response found yet."

@mcp.tool()
def store_artifact(job_id: str, filename: str, content: str) -> str:
    """
    Store an immutable artifact (code, document, etc.).
    """
    # Create a job-specific artifact folder
    job_artifact_dir = ARTIFACTS_DIR / job_id
    job_artifact_dir.mkdir(parents=True, exist_ok=True)

    file_path = job_artifact_dir / filename
    file_path.write_text(content)

    return f"Artifact stored: {file_path}"

if __name__ == "__main__":
    # When run directly, it uses stdio transport by default which is what we want for local apps
    mcp.run()
