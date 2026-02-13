import os
import logging
import google.generativeai as genai
from .base import BaseAgent

logger = logging.getLogger("Jules")

class Jules(BaseAgent):
    def __init__(self):
        super().__init__("jules")

        # Get key from config (which resolves env vars)
        api_key = self.agent_config.get("api_key")

        if not api_key:
            logger.warning("API key not found for Jules. Check config/env.")
        else:
            genai.configure(api_key=api_key)

        # Initialize model
        # Using Gemini 1.5 Flash as a reasonable default for an agent
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_response(self, chat_history: str) -> str:
        # Gemini Python SDK handles chat history via History object or just sending content
        # For a simple turn-based file agent, we can feed the whole history as prompt context.

        prompt = f"""You are Jules, a software engineering agent.
You are communicating via a shared log file.
Below is the history of the conversation:

{chat_history}

Please provide your response as Jules. Do not prefix with "**Jules**: " as that is handled by the system.
If the last message was from you, or if there is nothing relevant to add, you can reply with "[NO REPLY]" to skip.
"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if text == "[NO REPLY]":
                return ""
            return text
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return f"Error: {e}"

if __name__ == "__main__":
    agent = Jules()
    agent.process()
