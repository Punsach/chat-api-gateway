# app/llm.py
import time
import uuid
from typing import Generator

def mock_llm_stream(messages: list, model: str) -> Generator[str, None, None]:
    """
    Simulate streaming LLM response
    In production, this would call OpenAI/Anthropic API
    """
    # Build a simple prompt from messages
    prompt = messages[-1]["content"] if messages else "Hello"
    
    # Mock response based on prompt
    if "python" in prompt.lower():
        response = "Here's a Python example: def hello(): print('Hello, World!')"
    elif "joke" in prompt.lower():
        response = "Why do programmers prefer dark mode? Because light attracts bugs! 🐛"
    else:
        response = f"This is a mock response to: {prompt[:50]}. In production, this would stream from a real LLM."
    
    # Stream word by word
    words = response.split()
    for word in words:
        time.sleep(0.05)  # Simulate network delay
        yield word + " "

def mock_llm_complete(messages: list, model: str) -> str:
    """
    Simulate non-streaming LLM response
    """
    time.sleep(0.5)  # Simulate processing
    prompt = messages[-1]["content"] if messages else "Hello"
    
    if "python" in prompt.lower():
        return "Here's a Python example: def hello(): print('Hello, World!')"
    elif "joke" in prompt.lower():
        return "Why do programmers prefer dark mode? Because light attracts bugs! 🐛"
    else:
        return f"This is a mock response to: {prompt[:50]}. In production, this would stream from a real LLM."