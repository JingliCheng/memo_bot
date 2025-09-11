#!/usr/bin/env python3
"""
Profile Card Viewer - Development and Testing Tool

This script provides utilities for viewing and inspecting Profile Cards stored in Firestore.
It's primarily used for development, debugging, and testing purposes.

Usage:
    python tests/view_profile_cards.py
    python tests/view_profile_cards.py --user test_user_123
    python tests/view_profile_cards.py --history test_user_123
"""

import os
import sys
import argparse
from typing import Optional

# Add backend directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import firestore
from profile_card import ProfileCard

# Initialize Firestore
_PROJECT = os.getenv("FIRESTORE_PROJECT", "gen-lang-client-0574433212")
_db = firestore.Client(project=_PROJECT)

def list_all_users() -> None:
    """List all users who have Profile Cards."""
    print("=== All Users with Profile Cards ===")
    
    users_ref = _db.collection("users")
    users = users_ref.stream()
    
    user_count = 0
    for user_doc in users:
        user_id = user_doc.id
        profile_ref = user_doc.reference.collection("meta").document("profile_card")
        profile_doc = profile_ref.get()
        
        if profile_doc.exists:
            user_count += 1
            profile_data = profile_doc.to_dict()
            profile = ProfileCard(**profile_data)
            
            print(f"\n--- User: {user_id} ---")
            print(f"Version: {profile.version}")
            print(f"Total Facts: {profile.metadata.get('total_facts', 0)}")
            print(f"Last Updated: {profile.metadata.get('updated_at', 'Unknown')}")
            
            # Show some key facts
            demographics = profile.sections.get('demographics', {})
            if demographics.get('name', {}).get('value'):
                print(f"Name: {demographics['name']['value']}")
            if demographics.get('age', {}).get('value'):
                print(f"Age: {demographics['age']['value']}")
            if demographics.get('location', {}).get('value'):
                print(f"Location: {demographics['location']['value']}")
            
            # Show interests
            interests = profile.sections.get('interests', {}).get('primary_interests', {})
            if interests:
                print(f"Interests: {', '.join(interests.keys())}")
            
            # Show preferences
            prefs = profile.sections.get('preferences', {})
            for pref_type, pref_data in prefs.items():
                if pref_data:
                    print(f"{pref_type}: {', '.join(pref_data.keys())}")
    
    print(f"\nTotal users with Profile Cards: {user_count}")

def view_specific_user(user_id: str) -> None:
    """View detailed Profile Card for a specific user."""
    print(f"=== Profile Card for User: {user_id} ===")
    
    profile_ref = _db.collection("users").document(user_id).collection("meta").document("profile_card")
    profile_doc = profile_ref.get()
    
    if not profile_doc.exists:
        print(f"No Profile Card found for user: {user_id}")
        return
    
    profile_data = profile_doc.to_dict()
    profile = ProfileCard(**profile_data)
    
    print(f"Version: {profile.version}")
    print(f"Created: {profile.metadata.get('created_at', 'Unknown')}")
    print(f"Updated: {profile.metadata.get('updated_at', 'Unknown')}")
    print(f"Total Facts: {profile.metadata.get('total_facts', 0)}")
    
    print("\n--- Detailed Profile ---")
    for section_name, section_data in profile.sections.items():
        print(f"\n{section_name.upper()}:")
        
        if isinstance(section_data, dict):
            for field_name, field_data in section_data.items():
                if isinstance(field_data, dict):
                    if 'value' in field_data:
                        # Single value field
                        value = field_data.get('value', '')
                        confidence = field_data.get('confidence', 0)
                        count = field_data.get('count', 0)
                        if value:
                            print(f"  {field_name}: {value} (confidence: {confidence:.2f}, count: {count})")
                    else:
                        # Dictionary field (like interests, preferences)
                        if field_data:
                            print(f"  {field_name}:")
                            for item, item_data in field_data.items():
                                if isinstance(item_data, dict):
                                    confidence = item_data.get('confidence', 0)
                                    count = item_data.get('count', 0)
                                    print(f"    - {item} (confidence: {confidence:.2f}, count: {count})")
                                else:
                                    print(f"    - {item}")

def view_profile_history(user_id: str, limit: int = 5) -> None:
    """View Profile Card version history for a user."""
    print(f"=== Profile History for User: {user_id} ===")
    
    history_ref = _db.collection("users").document(user_id).collection("profile_history")
    history_docs = history_ref.order_by("version", direction=firestore.Query.DESCENDING).limit(limit).stream()
    
    for doc in history_docs:
        data = doc.to_dict()
        profile = ProfileCard(**data)
        
        print(f"\n--- Version {profile.version} ---")
        print(f"Updated: {profile.metadata.get('updated_at', 'Unknown')}")
        print(f"Total Facts: {profile.metadata.get('total_facts', 0)}")
        
        # Show what changed (simplified)
        demographics = profile.sections.get('demographics', {})
        if demographics.get('name', {}).get('value'):
            print(f"Name: {demographics['name']['value']}")

def main() -> None:
    """Main function to run the profile viewer."""
    parser = argparse.ArgumentParser(description="Profile Card Viewer - Development Tool")
    parser.add_argument("--user", help="View specific user's profile")
    parser.add_argument("--history", help="View user's profile history")
    parser.add_argument("--limit", type=int, default=5, help="Limit for history view")
    
    args = parser.parse_args()
    
    print("Profile Card Viewer - Development Tool")
    print("=" * 50)
    
    try:
        if args.user:
            view_specific_user(args.user)
        elif args.history:
            view_profile_history(args.history, args.limit)
        else:
            # Default: List all users
            list_all_users()
            
            print("\n" + "=" * 50)
            print("Usage Examples:")
            print("  python tests/view_profile_cards.py --user test_user_123")
            print("  python tests/view_profile_cards.py --history test_user_123 --limit 10")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
