import { useEffect, useState, useCallback } from "react";
import { getChromaData } from "./api";

/**
 * ChromaDB Inspection Component
 * 
 * Displays the contents of the local Chroma database for debugging purposes.
 * Shows episodes stored in the episodic_memory collection with their metadata.
 * 
 * @returns {JSX.Element} The ChromaDB inspection panel
 */
export default function ChromaInspection() {
  const [episodes, setEpisodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState(null);

  /**
   * Load Chroma DB data from the backend
   */
  const loadChromaData = useCallback(async (reset = true) => {
    if (reset) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError("");
    
    try {
      const data = await getChromaData();
      
      if (data.ok) {
        setEpisodes(data.episodes || []);
        setStats(data.stats || null);
      } else {
        setError(data.error || "Failed to load Chroma data");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChromaData(true);
  }, [loadChromaData]);

  /**
   * Format timestamp for display
   */
  const formatTimestamp = (timestamp) => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  /**
   * Truncate text for display
   */
  const truncateText = (text, maxLength = 100) => {
    if (!text) return "";
    return text.length > maxLength ? text.substring(0, maxLength) + "..." : text;
  };

  return (
    <div className="chroma-inspection-panel">
      <div className="chroma-inspection-header">
        <h3>🗄️ Chroma DB Inspector</h3>
        <button 
          className="refresh-button" 
          onClick={() => loadChromaData(true)} 
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {stats && (
        <div className="chroma-stats">
          <div className="stat-item">
            <span className="stat-label">Total Episodes:</span>
            <span className="stat-value">{stats.total_episodes}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Collection:</span>
            <span className="stat-value">{stats.collection_name}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Mode:</span>
            <span className="stat-value">{stats.chroma_mode}</span>
          </div>
          {stats.collection_exists !== undefined && (
            <div className="stat-item">
              <span className="stat-label">Status:</span>
              <span className="stat-value" style={{color: stats.collection_exists ? '#10b981' : '#f59e0b'}}>
                {stats.collection_exists ? 'Ready' : 'Empty'}
              </span>
            </div>
          )}
        </div>
      )}

      <div className="episodes-list">
        {episodes.length === 0 && !loading && !refreshing && (
          <div className="no-data">
            <div className="no-data-icon">🗄️</div>
            <div className="no-data-title">No Episodes Found</div>
            <div className="no-data-message">
              The Chroma database is empty. Episodes will appear here after you have conversations with the AI.
            </div>
          </div>
        )}

        {episodes.map((episode, index) => (
          <div key={episode.id || index} className="episode-item">
            <div className="episode-header">
              <div className="episode-id">
                <strong>ID:</strong> {episode.id}
              </div>
              <div className="episode-meta">
                <span className="episode-round">Round {episode.round_number}</span>
                <span className="episode-timestamp">
                  {formatTimestamp(episode.timestamp)}
                </span>
              </div>
            </div>
            
            <div className="episode-content">
              <div className="episode-message">
                <div className="message-label">User:</div>
                <div className="message-text">
                  {truncateText(episode.user_message, 150)}
                </div>
              </div>
              
              <div className="episode-message">
                <div className="message-label">AI:</div>
                <div className="message-text">
                  {truncateText(episode.ai_response, 150)}
                </div>
              </div>
            </div>

            <div className="episode-footer">
              <div className="episode-info">
                <span className="info-item">
                  <strong>Session:</strong> {episode.session_id}
                </span>
                <span className="info-item">
                  <strong>Tokens:</strong> {episode.tokens || 0}
                </span>
                {episode.similarity && (
                  <span className="info-item">
                    <strong>Similarity:</strong> {episode.similarity.toFixed(3)}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="loading-indicator">
            Loading episodes...
          </div>
        )}
      </div>

      <div className="chroma-info">
        <p className="info-text">
          This panel shows the contents of your local Chroma database. 
          Episodes are conversation rounds stored with embeddings for semantic search.
        </p>
      </div>
    </div>
  );
}
