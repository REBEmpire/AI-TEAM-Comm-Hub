
import sys
from unittest.mock import MagicMock
import unittest

# Mock dependencies
sys.modules['openai'] = MagicMock()
mock_yaml = MagicMock()
sys.modules['yaml'] = mock_yaml

# Mock config
mock_yaml.safe_load.return_value = {
    "agents": {
        "deep_agent": {"name": "Deep Agent", "api_key": "dummy"},
        "chatllm": {"name": "ChatLLM", "api_key": "dummy"}
    },
    "communication": {
        "log_file": "meeting_log.md"
    }
}

import os
sys.path.append(os.path.join(os.getcwd(), 'fortress-hivemind'))

from agents.deep_agent import DeepAgent
from agents.chatllm import ChatLLM

class TestParsing(unittest.TestCase):
    def setUp(self):
        # Sample history for testing
        self.history = """**Agent 1**: Hello world
This is a second line.

**Deep Agent**: Hi Agent 1
**ChatLLM**: I am here too.
"""

    def test_deep_agent_parsing(self):
        agent = DeepAgent()
        messages = agent._parse_history(self.history)

        # DeepAgent's name is "Deep Agent".
        # 1. user (Agent 1): Hello world\nThis is a second line.
        # 2. assistant (Deep Agent): Hi Agent 1
        # 3. user (ChatLLM): I am here too.

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]['role'], 'user')
        self.assertEqual(messages[0]['content'], "Hello world\nThis is a second line.")

        self.assertEqual(messages[1]['role'], 'assistant')
        self.assertEqual(messages[1]['content'], "Hi Agent 1")

        self.assertEqual(messages[2]['role'], 'user')
        self.assertEqual(messages[2]['content'], "I am here too.")

    def test_chatllm_parsing(self):
        agent = ChatLLM()
        messages = agent._parse_history(self.history)

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]['role'], 'user')
        self.assertEqual(messages[0]['content'], "Hello world\nThis is a second line.")

        self.assertEqual(messages[1]['role'], 'user')
        self.assertEqual(messages[1]['content'], "Hi Agent 1")

        self.assertEqual(messages[2]['role'], 'assistant')
        self.assertEqual(messages[2]['content'], "I am here too.")

if __name__ == '__main__':
    unittest.main()
