#!/usr/bin/env python3
"""
Test script to verify that the new config structure works correctly.
"""

import sys
import os

# Add the parent directory to the path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import config
    print("Config imported successfully!")
    print(f"Number of API keys: {len(config.GROQ_API_KEYS)}")
    print(f"Current API key index: {config.CURRENT_API_KEY_INDEX}")
    print(f"Current API key: {config.get_current_api_key()[:10]}...")
    
    # Test cycling through API keys
    print("\nTesting API key cycling:")
    for i in range(len(config.GROQ_API_KEYS) + 1):
        key = config.cycle_api_key()
        print(f"  Key {i+1}: {key[:10]}...")
        
except Exception as e:
    print(f"Error importing config: {e}")