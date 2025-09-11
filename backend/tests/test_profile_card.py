"""
Simple test script for Profile Card functionality.
"""
import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from profile_card import (
    create_default_profile_card, 
    get_profile_card, 
    save_profile_card,
    update_profile_with_confidence,
    format_profile_for_llm
)

def test_profile_card_creation():
    """Test creating a default profile card."""
    print("=== Testing Profile Card Creation ===")
    
    user_id = "test_user_123"
    profile = create_default_profile_card(user_id)
    
    print(f"Created profile for user: {user_id}")
    print(f"Version: {profile.version}")
    print(f"Sections: {list(profile.sections.keys())}")
    print(f"Total facts: {profile.metadata['total_facts']}")
    
    return profile

def test_profile_card_save_load():
    """Test saving and loading profile card."""
    print("\n=== Testing Profile Card Save/Load ===")
    
    user_id = "test_user_456"
    
    # Create and save profile
    profile = create_default_profile_card(user_id)
    success = save_profile_card(user_id, profile)
    print(f"Save successful: {success}")
    
    # Load profile
    loaded_profile = get_profile_card(user_id)
    print(f"Loaded profile version: {loaded_profile.version}")
    print(f"Loaded profile sections: {list(loaded_profile.sections.keys())}")
    
    return loaded_profile

def test_profile_card_updates():
    """Test updating profile card with confidence tracking."""
    print("\n=== Testing Profile Card Updates ===")
    
    user_id = "test_user_789"
    profile = create_default_profile_card(user_id)
    
    # Test updates
    updates = [
        {
            "section": "demographics",
            "field": "name",
            "value": "Alex",
            "confidence": 0.95,
            "reason": "User explicitly stated their name"
        },
        {
            "section": "preferences",
            "field": "favorite_animals",
            "value": "triceratops",
            "confidence": 0.90,
            "reason": "User mentioned loving triceratops"
        }
    ]
    
    # Update profile
    updated_profile = update_profile_with_confidence(profile, updates)
    
    print(f"Updated profile version: {updated_profile.version}")
    print(f"Name: {updated_profile.sections['demographics']['name']}")
    print(f"Favorite animals: {updated_profile.sections['preferences']['favorite_animals']}")
    
    return updated_profile

def test_profile_formatting():
    """Test formatting profile for LLM."""
    print("\n=== Testing Profile Formatting ===")
    
    user_id = "test_user_format"
    profile = create_default_profile_card(user_id)
    
    # Add some test data
    profile.sections['demographics']['name']['value'] = "Alex"
    profile.sections['demographics']['age']['value'] = "8"
    profile.sections['preferences']['favorite_animals']['triceratops'] = {
        "confidence": 0.95,
        "count": 3,
        "reasons": []
    }
    
    # Format for LLM
    formatted = format_profile_for_llm(profile)
    print("Formatted profile:")
    print(formatted)
    
    return formatted

def main():
    """Run all tests."""
    print("Profile Card Test Suite")
    print("=" * 50)
    
    try:
        # Test 1: Creation
        profile1 = test_profile_card_creation()
        
        # Test 2: Save/Load
        profile2 = test_profile_card_save_load()
        
        # Test 3: Updates
        profile3 = test_profile_card_updates()
        
        # Test 4: Formatting
        formatted = test_profile_formatting()
        
        print("\n=== All Tests Completed Successfully ===")
        
    except Exception as e:
        print(f"\n=== Test Failed: {e} ===")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
