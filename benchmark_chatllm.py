
import time
import re
import sys
from unittest.mock import MagicMock

# Mock dependencies that are missing in the environment
sys.modules['openai'] = MagicMock()
sys.modules['yaml'] = MagicMock()

# Import the class to test
import os
sys.path.append(os.path.join(os.getcwd(), 'fortress-hivemind'))

from agents.chatllm import ChatLLM

def benchmark_parse_history(iterations=1000):
    agent = ChatLLM()
    # Mock some history data
    history = "# Fortress HiveMind Meeting Log\n\n"
    for i in range(100):
        history += f"**Agent {i%4}**: This is message number {i}. It has some content.\n"
        history += "With multiple lines of content to make it more realistic.\n"

    start_time = time.time()
    for _ in range(iterations):
        agent._parse_history(history)
    end_time = time.time()

    return end_time - start_time

if __name__ == "__main__":
    duration = benchmark_parse_history()
    print(f"Baseline duration for 1000 iterations: {duration:.4f} seconds")
