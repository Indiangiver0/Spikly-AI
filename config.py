# config.py
import os

# Read the OpenAI API key from environment variable. Fallback to empty string to avoid hardcoding secrets.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")