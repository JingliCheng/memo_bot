import { useEffect, useState, useCallback } from "react";
import { getMessagesWithCache } from "./api";

export default function RecentMessages() {
  const [items, setItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const [pageSize] = useState(6);

  const load = useCallback(async (reset = true) => {
    if (reset) {
      setRefreshing(true);
      setPage(0);
    } else {
      setLoadingMore(true);
    }
    setError("");
    
    try {
      const offset = reset ? 0 : page * pageSize;
      const messages = await getMessagesWithCache(pageSize, offset);
      
      if (reset) {
        setItems(messages || []);
      } else {
        setItems(prev => [...prev, ...(messages || [])]);
      }
      
      setHasMore(messages && messages.length === pageSize);
      setPage(prev => prev + 1);
    } catch (e) {
      setError(String(e));
    } finally {
      setRefreshing(false);
      setLoadingMore(false);
    }
  }, [page, pageSize]);

  useEffect(() => { 
    load(true); 
  }, []);

  return (
    <div className="recent-messages-panel">
      <div className="recent-messages-header">
        <h3>💬 Recent Messages</h3>
        <button 
          className="refresh-button" 
          onClick={() => load(true)} 
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {error && <div className="error-message">{error}</div>}
      <div className="messages-list">
        {items.map((m, i) => (
          <div key={i} className={`message-item ${m.role}`}>
            <div className="message-role">
              {m.role === "user" ? "You" : "Talky Dino"}
            </div>
            <div className="message-content">{m.content}</div>
          </div>
        ))}
        {!items.length && <div className="no-data">No messages yet.</div>}
        {hasMore && (
          <button 
            className="load-more-button" 
            onClick={() => load(false)}
            disabled={loadingMore}
          >
            {loadingMore ? "Loading…" : "Load More"}
          </button>
        )}
      </div>
    </div>
  );
}