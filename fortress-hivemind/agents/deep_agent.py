import logging
import re
from openai import OpenAI, APIError
from .base import BaseAgent

logger = logging.getLogger("DeepAgent")

class DeepAgent(BaseAgent):
    def __init__(self):
        super().__init__("deep_agent")
        # Abacus RouteLLM uses OpenAI-compatible interface
        self.client = OpenAI(
            base_url="https://routellm.abacus.ai/v1",
            api_key=self.agent_config["api_key"]
        )

    def _parse_history(self, history: str) -> list:
        """Parses the markdown log into message format."""
        messages = []
        lines = history.split('\n')
        current_msg_parts = []
        current_role = "user"

        for line in lines:
            if not line.strip():
                continue

            match = re.match(r"\*\*(.+?)\*\*: (.*)", line)
            if match:
                speaker, content = match.groups()
                if current_msg_parts:
                    messages.append({"role": current_role, "content": "\n".join(current_msg_parts).strip()})

                current_msg_parts = [content]
                current_role = "assistant" if speaker == self.name else "user"
            else:
                current_msg_parts.append(line)

        if current_msg_parts:
            messages.append({"role": current_role, "content": "\n".join(current_msg_parts).strip()})

        return messages

    def generate_response(self, chat_history: str) -> str:
        messages = self._parse_history(chat_history)
        if not messages:
            messages = [{"role": "user", "content": "Hello."}]

        try:
            logger.info(f"Sending {len(messages)} messages to Abacus RouteLLM.")
            response = self.client.chat.completions.create(
                model="route-llm", # As per user instructions
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content

        except APIError as e:
            logger.error(f"Abacus RouteLLM API Error: {e}")
            return f"Error communicating with Deep Agent: {e}"

if __name__ == "__main__":
    agent = DeepAgent()
    agent.process()
