import { useEffect, useState, useCallback } from "react";
import { ensureAnonUser, getAuthHeader } from "./firebase";


export default function RecentMessages({ baseUrl = "http://localhost:8000" }) {
  const [items, setItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setRefreshing(true);
    setError("");
    try {
      // Ensure authentication is ready before making API calls
      await ensureAnonUser();
      const headers = await getAuthHeader();
      const resp = await fetch(`${baseUrl}/api/messages?limit=12`, { headers });
        
      const data = await resp.json();
      if (!data?.ok) throw new Error("Request failed");
      setItems(data.items || []);
    } catch (e) {
      setError(String(e));
    } finally {
      setRefreshing(false);
    }
  }, [baseUrl]);

  useEffect(() => { 
    load(); 
  }, [load]);

  return (
    <div className="border rounded p-3 bg-white">
      <div className="flex items-center justify-between mb-2">
        <b>Recent (server)</b>
        <button className="text-sm underline" onClick={load} disabled={refreshing}>
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {error && <div className="text-red-600 text-sm mb-2">{error}</div>}
      <div className="space-y-1 text-sm">
        {items.map((m, i) => (
          <div key={i}>
            <b>{m.role === "user" ? "You" : "Bot"}:</b> {m.content}
          </div>
        ))}
        {!items.length && <div className="opacity-60">No messages yet.</div>}
      </div>
    </div>
  );
}
