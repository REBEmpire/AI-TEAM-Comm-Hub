import os
import logging
import httpx
import json
from .base import BaseAgent

logger = logging.getLogger("GeminiRaw")

class GeminiRaw(BaseAgent):
    def __init__(self):
        super().__init__("gemini")
        # Config loading in BaseAgent resolves os.environ/ placeholders
        self.api_key = self.agent_config.get("api_key")

    def generate_response(self, chat_history: str) -> str:
        if not self.api_key:
            return "Error: Missing GEMINI_API_KEY"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"

        system_instruction = "You are Gemini, a helpful AI assistant. You are participating in a team meeting."

        prompt = f"""Here is the meeting log so far:
{chat_history}

Please reply to the latest message if appropriate."""

        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.8}
        }

        try:
            response = httpx.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            # Extract text
            # Response format: candidates[0].content.parts[0].text
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text
            except (KeyError, IndexError):
                logger.error(f"Unexpected response format: {data}")
                return "Error parsing response."

        except Exception as e:
            logger.error(f"HTTP Error: {e}")
            return f"Error: {e}"

if __name__ == "__main__":
    agent = GeminiRaw()
    agent.process()
