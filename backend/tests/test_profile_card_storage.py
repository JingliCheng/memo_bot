"""
Test script to create and store a Profile Card, then view it.
"""
import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from profile_card import create_default_profile_card, save_profile_card, get_profile_card
from .view_profile_cards import view_specific_user

# Set the project ID for testing
os.environ["FIRESTORE_PROJECT"] = "gen-lang-client-0574433212"

def test_create_and_store_profile():
    """Create a test Profile Card and store it."""
    print("=== Creating Test Profile Card ===")
    
    user_id = "test_user_demo"
    
    # Create default profile
    profile = create_default_profile_card(user_id)
    
    # Add some test data
    profile.sections['demographics']['name']['value'] = "Alex"
    profile.sections['demographics']['name']['confidence'] = 0.95
    profile.sections['demographics']['name']['count'] = 1
    
    profile.sections['demographics']['age']['value'] = "8"
    profile.sections['demographics']['age']['confidence'] = 0.90
    profile.sections['demographics']['age']['count'] = 1
    
    profile.sections['preferences']['favorite_animals']['triceratops'] = {
        "confidence": 0.95,
        "count": 3,
        "reasons": []
    }
    
    profile.sections['preferences']['favorite_animals']['stegosaurus'] = {
        "confidence": 0.90,
        "count": 2,
        "reasons": []
    }
    
    profile.sections['interests']['primary_interests']['dinosaurs'] = {
        "confidence": 0.95,
        "count": 5,
        "reasons": []
    }
    
    profile.sections['interests']['primary_interests']['space'] = {
        "confidence": 0.85,
        "count": 2,
        "reasons": []
    }
    
    # Save profile
    success = save_profile_card(user_id, profile)
    print(f"Profile saved successfully: {success}")
    
    # Load and verify
    loaded_profile = get_profile_card(user_id)
    print(f"Loaded profile version: {loaded_profile.version}")
    print(f"Loaded profile total facts: {loaded_profile.metadata['total_facts']}")
    
    return user_id

def main():
    """Main function."""
    print("Profile Card Storage Test")
    print("=" * 50)
    
    try:
        # Create test profile
        user_id = test_create_and_store_profile()
        
        # View the stored profile
        print("\n" + "=" * 50)
        view_specific_user(user_id)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
