import { useEffect, useState, useCallback } from "react";
import { getMessages } from "./api";

export default function RecentMessages() {
  const [items, setItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setRefreshing(true);
    setError("");
    try {
      const messages = await getMessages(12);
      setItems(messages || []);
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
    <div className="recent-messages-panel">
      <div className="recent-messages-header">
        <h3>💬 Recent Messages</h3>
        <button 
          className="refresh-button" 
          onClick={load} 
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
      </div>
    </div>
  );
}