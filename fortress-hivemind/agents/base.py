import os
import subprocess
import yaml
import logging
from abc import ABC, abstractmethod
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BaseAgent")

class BaseAgent(ABC):
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.root_dir = Path(__file__).parent.parent.resolve()
        self.config_path = self.root_dir / "agents" / "config.yaml"
        self.config = self._load_config()
        self.agent_config = self.config["agents"].get(agent_id, {})
        self.name = self.agent_config.get("name", agent_id)
        self.log_file = self.root_dir / self.config["communication"]["log_file"]

    def _load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found at {self.config_path}")
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)
        return self._resolve_env_vars(config)

    def _resolve_env_vars(self, config):
        """Recursively resolves os.environ/VAR strings in the config."""
        if isinstance(config, dict):
            return {k: self._resolve_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_vars(i) for i in config]
        elif isinstance(config, str) and config.startswith("os.environ/"):
            env_var = config.split("/", 1)[1]
            return os.getenv(env_var)
        return config

    def _run_git_command(self, args: list):
        """Runs a git command in the repo root."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Git command '{' '.join(args)}' success.")
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command '{' '.join(args)}' failed: {e.stderr}")
            # We don't raise here because some commands like 'git pull' might fail if no upstream,
            # but we might still want to proceed with local testing.
            return None

    def sync_repo(self):
        """Pulls the latest changes."""
        logger.info("Syncing repository...")
        # Stash local changes just in case, to avoid conflicts
        self._run_git_command(["stash"])
        self._run_git_command(["pull", "--rebase"])
        self._run_git_command(["stash", "pop"])

    def read_log(self):
        """Reads the meeting log."""
        if not self.log_file.exists():
            return ""
        with open(self.log_file, "r") as f:
            return f.read()

    def append_to_log(self, message: str):
        """Appends a message to the meeting log."""
        entry = f"\n\n**{self.name}**: {message}\n"
        with open(self.log_file, "a") as f:
            f.write(entry)
        return entry

    def commit_and_push(self, message: str):
        """Commits changes and pushes."""
        self._run_git_command(["add", str(self.log_file.name)])
        self._run_git_command(["commit", "-m", f"{self.name}: {message[:50]}..."])
        self._run_git_command(["push"])

    @abstractmethod
    def generate_response(self, chat_history: str) -> str:
        """Generates a response based on the chat history."""
        pass

    def process(self):
        """Main execution flow."""
        logger.info(f"Agent {self.name} starting process cycle.")

        # 1. Sync
        self.sync_repo()

        # 2. Read
        history = self.read_log()

        # 3. Decide if we should reply
        # For this implementation, we will always try to reply if the last message wasn't us.
        # But to avoid infinite loops in a real system, we might want smarter logic.
        # For now, we will rely on the specific agent implementation to decide OR
        # just assume if called, it's expected to work.
        # However, to prevent self-reply loops:
        last_lines = history.strip().split('\n')
        if last_lines and last_lines[-1].startswith(f"**{self.name}**"):
            logger.info("Last message was mine. Skipping.")
            return

        # 4. Generate
        logger.info("Generating response...")
        response = self.generate_response(history)

        if response:
            # 5. Write
            self.append_to_log(response)

            # 6. Push
            self.commit_and_push(response)
            logger.info("Response posted and pushed.")
        else:
            logger.info("No response generated.")
