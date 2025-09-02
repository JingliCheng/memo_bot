import { useEffect, useState, useCallback } from "react";
import { getMemories } from "./api";

export default function MemoryPeek() {
  const [items, setItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setRefreshing(true);
    setError("");
    try {
      const memories = await getMemories(12);
      setItems(memories || []);
    } catch (e) {
      setError(String(e));
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { 
    load(); 
  }, [load]);

  return (
    <div className="memory-peek-panel">
      <div className="memory-peek-header">
        <h3>🧠 Memory Peek</h3>
        <button 
          className="refresh-button" 
          onClick={load} 
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
      </div>
    </div>
  );
}