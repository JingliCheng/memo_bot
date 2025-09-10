#!/usr/bin/env python3
"""
Chroma Configuration Helper
Shows current configuration and helps switch between local and cloud modes.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def show_current_config():
    """Display current Chroma configuration."""
    print("=== Current Chroma Configuration ===")
    
    chroma_mode = os.getenv("CHROMA_MODE", "local").lower()
    print(f"Mode: {chroma_mode.upper()}")
    
    if chroma_mode == "cloud":
        print("\nCloud Configuration:")
        print(f"  CHROMA_API_KEY: {'✓ Set' if os.getenv('CHROMA_API_KEY') else '✗ Missing'}")
        print(f"  CHROMA_TENANT: {'✓ Set' if os.getenv('CHROMA_TENANT') else '✗ Missing'}")
        print(f"  CHROMA_DATABASE: {'✓ Set' if os.getenv('CHROMA_DATABASE') else '✗ Missing'}")
    else:
        print("\nLocal Configuration:")
        print("  Database: ./chroma_db/")
        print("  Persistence: Enabled")
    
    print(f"\nOpenAI API Key: {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Missing'}")
    
    # Check if local database exists
    if chroma_mode == "local":
        if os.path.exists("./chroma_db"):
            print("  Local database: ✓ Exists")
        else:
            print("  Local database: ✗ Not created yet")

def switch_to_local():
    """Switch to local Chroma mode."""
    print("Switching to LOCAL Chroma mode...")
    print("Set CHROMA_MODE=local in your .env file")
    print("No additional environment variables needed for local mode.")

def switch_to_cloud():
    """Switch to Chroma Cloud mode."""
    print("Switching to CHROMA CLOUD mode...")
    print("Set the following in your .env file:")
    print("CHROMA_MODE=cloud")
    print("CHROMA_API_KEY=your_api_key")
    print("CHROMA_TENANT=your_tenant_id")
    print("CHROMA_DATABASE=your_database_name")

if __name__ == "__main__":
    show_current_config()
    
    print("\n=== Quick Commands ===")
    print("To switch to local:  CHROMA_MODE=local")
    print("To switch to cloud:  CHROMA_MODE=cloud")
    print("\nRun 'python test_episodic_memory.py' to test the current configuration.")
