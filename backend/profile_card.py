"""
Profile Card management system with MECE structure and confidence tracking.

This module provides a comprehensive user profiling system that:
- Maintains a MECE (Mutually Exclusive, Collectively Exhaustive) structure
- Tracks confidence levels for each fact
- Provides version history and validation
- Integrates with Firestore for persistence
"""

from __future__ import annotations
import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

load_dotenv()

# Firestore client configuration
_PROJECT = os.getenv("FIRESTORE_PROJECT")
_db = firestore.Client(project=_PROJECT)

# Data structures
@dataclass
class FactEntry:
    """Represents a single fact with confidence and count tracking."""
    value: str
    confidence: float
    count: int
    reasons: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []

@dataclass
class ProfileCard:
    """MECE Profile Card structure for comprehensive user profiling."""
    id: str
    user_id: str
    version: int
    sections: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

# Profile card creation and management
def create_default_profile_card(user_id: str) -> ProfileCard:
    """Create a default empty profile card."""
    return ProfileCard(
        id="profile_card",
        user_id=user_id,
        version=1,
        sections={
            "demographics": {
                "name": {"value": "", "confidence": 0.0, "count": 0, "reasons": []},
                "age": {"value": "", "confidence": 0.0, "count": 0, "reasons": []},
                "gender": {"value": "", "confidence": 0.0, "count": 0, "reasons": []},
                "location": {"value": "", "confidence": 0.0, "count": 0, "reasons": []}
            },
            "interests": {
                "primary_interests": {},
                "secondary_interests": {}
            },
            "preferences": {
                "favorite_animals": {},
                "favorite_foods": {},
                "favorite_colors": {},
                "favorite_activities": {}
            },
            "constraints": {
                "safety_limits": {},
                "schedule_limits": {},
                "health_limits": {}
            },
            "goals": {
                "learning_goals": {},
                "personal_goals": {}
            },
            "context": {
                "recent_events": {},
                "current_projects": {}
            },
            "communication": {
                "style": {"value": "", "confidence": 0.0, "count": 0, "reasons": []},
                "learning_level": {"value": "", "confidence": 0.0, "count": 0, "reasons": []},
                "attention_span": {"value": "", "confidence": 0.0, "count": 0, "reasons": []},
                "language_preference": {"value": "English", "confidence": 0.95, "count": 1, "reasons": []}
            }
        },
        metadata={
            "created_at": time.time(),
            "updated_at": time.time(),
            "last_consolidated": time.time(),
            "total_facts": 0
        }
    )

# Firestore operations
def _get_profile_ref(user_id: str):
    """Get Firestore reference for user's profile card."""
    return _db.collection("users").document(user_id).collection("meta").document("profile_card")

def get_profile_card(user_id: str) -> ProfileCard:
    """Get user's profile card from Firestore."""
    try:
        ref = _get_profile_ref(user_id)
        doc = ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            return ProfileCard(**data)
        else:
            # Create default profile card if none exists
            profile = create_default_profile_card(user_id)
            save_profile_card(user_id, profile)
            return profile
            
    except Exception as e:
        print(f"Error getting profile card for user {user_id}: {e}")
        # Return default profile card on error
        return create_default_profile_card(user_id)

def save_profile_card(user_id: str, profile: ProfileCard) -> bool:
    """Save profile card to Firestore."""
    try:
        ref = _get_profile_ref(user_id)
        
        # Update metadata
        profile.metadata["updated_at"] = time.time()
        profile.metadata["total_facts"] = count_total_facts(profile)
        
        # Convert to dict and save
        data = asdict(profile)
        ref.set(data)
        
        # Save version history
        save_profile_version(user_id, profile)
        
        return True
        
    except Exception as e:
        print(f"Error saving profile card for user {user_id}: {e}")
        return False

def save_profile_version(user_id: str, profile: ProfileCard) -> bool:
    """Save profile card version to history."""
    try:
        version_ref = _db.collection("users").document(user_id).collection("profile_history").document(f"v{profile.version}")
        version_ref.set(asdict(profile))
        return True
    except Exception as e:
        print(f"Error saving profile version for user {user_id}: {e}")
        return False

def get_profile_history(user_id: str, limit: int = 10) -> List[ProfileCard]:
    """Get profile card version history."""
    try:
        ref = _db.collection("users").document(user_id).collection("profile_history")
        docs = ref.order_by("version", direction=firestore.Query.DESCENDING).limit(limit).stream()
        
        profiles = []
        for doc in docs:
            data = doc.to_dict()
            profiles.append(ProfileCard(**data))
        
        return profiles
        
    except Exception as e:
        print(f"Error getting profile history for user {user_id}: {e}")
        return []

# Profile card operations
def count_total_facts(profile: ProfileCard) -> int:
    """Count total facts in profile card."""
    count = 0
    
    for section_name, section_data in profile.sections.items():
        if isinstance(section_data, dict):
            for field_name, field_data in section_data.items():
                if isinstance(field_data, dict):
                    if "value" in field_data:
                        # Single value field
                        if field_data["value"]:
                            count += 1
                    else:
                        # Dictionary field (like interests, preferences)
                        count += len(field_data)
    
    return count

def format_profile_for_llm(profile: ProfileCard) -> str:
    """Format profile card for LLM context injection."""
    sections = profile.sections
    
    context = f"""User Profile:
Name: {sections['demographics']['name']['value']}, Age: {sections['demographics']['age']['value']}
Location: {sections['demographics']['location']['value']}

Interests: {', '.join(sections['interests']['primary_interests'].keys())}

Preferences:
- Favorite animals: {', '.join(sections['preferences']['favorite_animals'].keys())}
- Favorite foods: {', '.join(sections['preferences']['favorite_foods'].keys())}
- Favorite colors: {', '.join(sections['preferences']['favorite_colors'].keys())}

Constraints:
- Safety: {', '.join(sections['constraints']['safety_limits'].keys())}
- Schedule: {', '.join(sections['constraints']['schedule_limits'].keys())}
- Health: {', '.join(sections['constraints']['health_limits'].keys())}

Current Context:
- Goals: {', '.join(sections['goals']['learning_goals'].keys())}
- Recent events: {', '.join(sections['context']['recent_events'].keys())}

Communication Style: {sections['communication']['style']['value']}
Learning Level: {sections['communication']['learning_level']['value']}
"""
    
    return context

def calculate_tokens(profile: ProfileCard) -> int:
    """Calculate token count for profile card."""
    text = format_profile_for_llm(profile)
    # Rough token estimation (1 token ≈ 4 characters)
    return len(text) // 4

# Profile update operations
def update_profile_with_confidence(profile: ProfileCard, updates: List[Dict[str, Any]]) -> ProfileCard:
    """Update profile card with confidence tracking."""
    
    for update in updates:
        section = update["section"]
        field = update["field"]
        value = update["value"]
        new_confidence = update["confidence"]
        reason = update["reason"]
        
        if section in profile.sections and field in profile.sections[section]:
            current = profile.sections[section][field]
            
            # Update count
            current["count"] = current.get("count", 0) + 1
            
            # Update confidence (weighted average)
            old_confidence = current.get("confidence", 0)
            old_count = current.get("count", 1)
            
            # Weighted average confidence
            new_avg_confidence = (old_confidence * old_count + new_confidence) / (old_count + 1)
            current["confidence"] = new_avg_confidence
            
            # Update value if confidence increased significantly
            if new_confidence > old_confidence + 0.1:
                current["value"] = value
            
            # Add reason to history
            if "reasons" not in current:
                current["reasons"] = []
            current["reasons"].append({
                "reason": reason,
                "confidence": new_confidence,
                "timestamp": time.time()
            })
    
    # Increment version
    profile.version += 1
    
    return profile

def validate_updates(updates: List[Dict[str, Any]], profile: ProfileCard) -> List[Dict[str, Any]]:
    """Validate that updates are actually new information."""
    
    validated = []
    
    for update in updates:
        section = update["section"]
        field = update["field"]
        value = update["value"]
        
        # Check if this information is already in the profile
        if section in profile.sections and field in profile.sections[section]:
            current_value = profile.sections[section][field]
            
            # If it's a single value field
            if "value" in current_value:
                if current_value["value"] == value:
                    continue  # Skip duplicate
            
            # If it's a dictionary field (like preferences), check if value exists
            elif isinstance(current_value, dict) and value in current_value:
                continue  # Skip duplicate
        
        validated.append(update)
    
    return validated

# Information detection
def contains_new_information(user_message: str) -> bool:
    """Quick check if conversation might contain new information."""
    
    # Check for explicit information sharing patterns
    new_info_patterns = [
        "I am", "I'm", "I have", "I like", "I love", "I hate", "I can't",
        "My name is", "I live in", "I work at", "I go to",
        "I'm allergic to", "I can't eat", "I don't like",
        "My favorite", "I prefer", "I want to", "I'm trying to"
    ]
    
    # Check if user message contains these patterns
    for pattern in new_info_patterns:
        if pattern.lower() in user_message.lower():
            return True
    
    return False

# Version information
VERSION_TAG = "profile_card v1.0 MECE"
