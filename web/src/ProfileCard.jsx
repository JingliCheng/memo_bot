import React, { useState, useEffect } from 'react';
import './ProfileCard.css';
import { getIdToken } from './firebase.js';

const ProfileCard = () => {
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    loadProfileCard();
  }, []);

  const loadProfileCard = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get auth token
      const token = await getIdToken();
      if (!token) {
        throw new Error('No authentication token available');
      }

      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      // Fetch profile card
      const response = await fetch(`${API_BASE_URL}/api/profile-card`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to load profile: ${response.status}`);
      }

      const data = await response.json();
      setProfileData(data.profile);

      // Also fetch stats
      const statsResponse = await fetch(`${API_BASE_URL}/api/profile-card/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData.stats);
      }

    } catch (err) {
      console.error('Error loading profile card:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatConfidence = (confidence) => {
    return Math.round(confidence * 100);
  };

  const renderSection = (sectionName, sectionData) => {
    if (!sectionData || Object.keys(sectionData).length === 0) {
      return null;
    }

    return (
      <div key={sectionName} className="profile-section">
        <h4 className="section-title">{sectionName.replace(/_/g, ' ').toUpperCase()}</h4>
        <div className="section-content">
          {Object.entries(sectionData).map(([fieldName, fieldData]) => {
            if (typeof fieldData === 'object' && fieldData !== null) {
              if (fieldData.value !== undefined) {
                // Single value field (like demographics)
                return (
                  <div key={fieldName} className="profile-item">
                    <span className="field-name">{fieldName.replace(/_/g, ' ')}:</span>
                    <span className="field-value">{fieldData.value}</span>
                    {fieldData.confidence && (
                      <span className="confidence-badge">
                        {formatConfidence(fieldData.confidence)}%
                      </span>
                    )}
                  </div>
                );
              } else {
                // Dictionary field (like preferences, interests)
                const items = Object.entries(fieldData);
                if (items.length === 0) return null;
                
                return (
                  <div key={fieldName} className="profile-item">
                    <span className="field-name">{fieldName.replace(/_/g, ' ')}:</span>
                    <div className="field-list">
                      {items.map(([item, itemData]) => (
                        <div key={item} className="list-item">
                          <span className="item-name">{item}</span>
                          {itemData.confidence && (
                            <span className="confidence-badge">
                              {formatConfidence(itemData.confidence)}%
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              }
            }
            return null;
          })}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="profile-card">
        <div className="profile-header">
          <h3>Profile Card</h3>
        </div>
        <div className="profile-content">
          <div className="loading">Loading profile...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="profile-card">
        <div className="profile-header">
          <h3>Profile Card</h3>
        </div>
        <div className="profile-content">
          <div className="error">
            <p>Error loading profile: {error}</p>
            <button onClick={loadProfileCard} className="retry-button">
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!profileData) {
    return (
      <div className="profile-card">
        <div className="profile-header">
          <h3>Profile Card</h3>
        </div>
        <div className="profile-content">
          <div className="empty-state">
            <p>No profile data available</p>
            <button onClick={loadProfileCard} className="retry-button">
              Load Profile
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-card">
      <div className="profile-header">
        <h3>Profile Card</h3>
        {stats && (
          <div className="profile-stats">
            <span className="stat-item">
              <strong>{stats.total_facts}</strong> facts
            </span>
            <span className="stat-item">
              v{stats.version}
            </span>
          </div>
        )}
      </div>
      
      <div className="profile-content">
        {Object.entries(profileData.sections).map(([sectionName, sectionData]) => 
          renderSection(sectionName, sectionData)
        )}
        
        {stats && (
          <div className="profile-footer">
            <div className="footer-stats">
              <div className="footer-stat">
                <span className="stat-label">Tokens:</span>
                <span className="stat-value">{stats.tokens}</span>
              </div>
              <div className="footer-stat">
                <span className="stat-label">Last Updated:</span>
                <span className="stat-value">
                  {stats.last_updated ? 
                    new Date(stats.last_updated * 1000).toLocaleDateString() : 
                    'Unknown'
                  }
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};


export default ProfileCard;
