import { useEffect, useState, useCallback } from "react";
import { getMemoriesWithCache } from "./api";

export default function MemoryPeek() {
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
      const memories = await getMemoriesWithCache(pageSize, offset);
      
      if (reset) {
        setItems(memories || []);
      } else {
        setItems(prev => [...prev, ...(memories || [])]);
      }
      
      setHasMore(memories && memories.length === pageSize);
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
    <div className="memory-peek-panel">
      <div className="memory-peek-header">
        <h3>🧠 Memory Peek</h3>
        <button 
          className="refresh-button" 
          onClick={() => load(true)} 
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {error && <div className="error-message">{error}</div>}
      <div className="memory-list">
        {items.map((m) => (
          <div key={m.id || `${m.key}:${m.value}`} className="memory-item">
            <div className="memory-key">{m.key}</div>
            <div className="memory-value">{m.value}</div>
            <div className="memory-meta">
              Salience: {Number(m.salience ?? 1).toFixed(2)} · 
              Confidence: {Number(m.confidence ?? 1).toFixed(2)}
            </div>
          </div>
        ))}
        {!items.length && <div className="no-data">No memories yet.</div>}
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