# Configuration settings for the resume parser and quiz generator

import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Groq API keys (stored in an array to cycle through if one runs out of credits)
# Keys are loaded from the environment variable 'GROQ_API_KEYS' as a JSON string
env_keys = os.getenv("GROQ_API_KEYS")
if env_keys:
    try:
        GROQ_API_KEYS = json.loads(env_keys)
    except json.JSONDecodeError:
        # Fallback if it's just a single key string or malformed
        GROQ_API_KEYS = [env_keys]
else:
    # Use a dummy key if nothing is found (prevents crash, but API calls will fail)
    GROQ_API_KEYS = ["MISSING_API_KEY"]

# Current API key index (starts at 0)
CURRENT_API_KEY_INDEX = 0

# Function to get the current API key
def get_current_api_key():
    if not GROQ_API_KEYS:
         return None
    return GROQ_API_KEYS[CURRENT_API_KEY_INDEX]

# Function to cycle to the next API key
def cycle_api_key():
    global CURRENT_API_KEY_INDEX
    if not GROQ_API_KEYS:
        return None
    CURRENT_API_KEY_INDEX = (CURRENT_API_KEY_INDEX + 1) % len(GROQ_API_KEYS)
    return get_current_api_key()

# Model settings
MODEL_NAME = "moonshotai/kimi-k2-instruct-0905"
TEMPERATURE = 0.2

#--------------------------------------Part 2 Constants-------------------------------------
# Quiz data directory
QUIZ_DATA_DIR = "Part2/QuizData"

# Default number of questions per quiz
DEFAULT_NUM_QUESTIONS = 10