#!/usr/bin/env python3
"""
Test script for episodic memory system.
Run this to verify Chroma Cloud integration and episode storage/retrieval.
"""
import os
import sys
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from episodic_memory import test_episodic_memory

if __name__ == "__main__":
    print("Starting Episodic Memory Test...")
    
    # Check which mode is being used
    chroma_mode = os.getenv("CHROMA_MODE", "local").lower()
    if chroma_mode == "cloud":
        print("Using CHROMA CLOUD")
        print("Required environment variables:")
        print("- CHROMA_API_KEY")
        print("- CHROMA_TENANT") 
        print("- CHROMA_DATABASE")
        print("- OPENAI_API_KEY")
    else:
        print("Using LOCAL Chroma database (stored in ./chroma_db/)")
        print("Required environment variables:")
        print("- OPENAI_API_KEY (for embeddings)")
        print("- CHROMA_MODE=local (optional, default)")
    print()
    
    try:
        test_episodic_memory()
    except Exception as e:
        print(f"Test failed with error: {e}")
        print("Please check your environment variables and configuration.")
