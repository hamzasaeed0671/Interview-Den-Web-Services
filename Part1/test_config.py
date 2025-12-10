#!/usr/bin/env python3
"""
Test script to verify that the config is being imported correctly.
"""

import sys
import os

# Add the parent directory to the path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import config
    print("Config imported successfully!")
    print(f"Config module file: {config.__file__}")
    
    # Set some test values
    config.GROQ_API_KEYS = ["test_key_1", "test_key_2"]
    config.MODEL_NAME = "test-model"
    config.TEMPERATURE = 0.5
    config.QUIZ_DATA_DIR = "test_quiz_dir"
    config.DEFAULT_NUM_QUESTIONS = 5
    
    print(f"Number of API keys: {len(config.GROQ_API_KEYS)}")
    
    # Print all API keys (first 10 chars for security)
    for i, key in enumerate(config.GROQ_API_KEYS):
        print(f"API Key {i+1}: {key[:10]}...")
    
    print(f"Current API key index: {config.CURRENT_API_KEY_INDEX}")
    print(f"Current API key: {config.get_current_api_key()[:10]}...")
    print(f"Model name: {config.MODEL_NAME}")
    print(f"Temperature: {config.TEMPERATURE}")
    print(f"Quiz data directory: {config.QUIZ_DATA_DIR}")
    print(f"Default number of questions: {config.DEFAULT_NUM_QUESTIONS}")
    
    # Test cycling through API keys
    print("\nTesting API key cycling:")
    for i in range(len(config.GROQ_API_KEYS)):
        key = config.cycle_api_key()
        print(f"  Key {i+1}: {key[:10]}...")
        
except Exception as e:
    print(f"Error importing config: {e}")
    import traceback
    traceback.print_exc()