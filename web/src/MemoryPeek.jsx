import { useEffect, useState, useCallback } from "react";
import { ensureAnonUser, getAuthHeader } from "./firebase";

export default function MemoryPeek({ baseUrl = "http://localhost:8000" }) {
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
      const resp = await fetch(`${baseUrl}/api/memory?limit=12`, { headers });
        
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
        <b>Memory (top)</b>
        <button className="text-sm underline" onClick={load} disabled={refreshing}>
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {error && <div className="text-red-600 text-sm mb-2">{error}</div>}
      <ul className="list-disc pl-5 space-y-1">
        {items.map((m) => (
          <li key={m.id || `${m.key}:${m.value}`}>
            <span className="font-semibold">{m.key}</span>: {m.value}
            <span className="opacity-60 text-xs">{" "}
              (s:{Number(m.salience ?? 1).toFixed(2)} · c:{Number(m.confidence ?? 1).toFixed(2)})
            </span>
          </li>
        ))}
        {!items.length && <li className="opacity-60">No memories yet.</li>}
      </ul>
    </div>
  );
}
