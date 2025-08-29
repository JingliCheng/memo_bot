import { useEffect, useState, useRef } from "react";
import MemoryPeek from "./MemoryPeek";
import RecentMessages from "./RecentMessages";
import { ensureAnonUser, getAuthHeader } from "./firebase";


export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const controllerRef = useRef(null);
//   const baseUrl = "http://localhost:8000";
  const baseUrl = "https://ai-companion-backend-420724880490.us-central1.run.app";
  const [uid, setUid] = useState(null); // for display only

  useEffect(() => {
    (async () => {
      try {
        await ensureAnonUser();
        const headers = await getAuthHeader();
        const r = await fetch(`${baseUrl}/whoami`, { headers });
        if (r.ok) {
          const j = await r.json();
          setUid(j.uid);
        } else {
          console.error("Failed to get user ID:", r.status, r.statusText);
        }
      } catch (error) {
        console.error("Authentication error:", error);
      }
    })();
  }, []);

  async function send() {
    if (!input.trim() || loading) return;
    setLoading(true);
    const userMsg = { role: "user", content: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");

    controllerRef.current = new AbortController();
    
    const headers = { "Content-Type": "application/json", ...(await getAuthHeader()) };

    const resp = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      headers,
      signal: controllerRef.current.signal,
      body: JSON.stringify({ message: userMsg.content }), // no uid needed anymore
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let assistant = { role: "assistant", content: "" };
    setMessages((m) => [...m, assistant]);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      for (const line of chunk.split("\n\n")) {
        if (!line.startsWith("data:")) continue;
        const data = line.slice(5).trim();
        if (data === "[DONE]") {
          setLoading(false);
          return;
        }
        try {
          const token = JSON.parse(data);
          assistant = { role: "assistant", content: (assistant.content || "") + token };
          setMessages((m) => [...m.slice(0, -1), assistant]);
        } catch (e) {
          console.error("Error parsing chunk:", e);
        }
      }
    }
    setLoading(false);
  }

  return (
    <div className="p-6 max-w-5xl mx-auto font-sans">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">AI Companion (MVP)</h1>
        {uid && (
          <div className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-mono">
            UID: {uid.substring(0, 8)}...
          </div>
        )}
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="col-span-2 border rounded p-3 h-96 overflow-auto bg-white">
          {messages.map((m, i) => (
            <div key={i} className="mb-2">
              <b>{m.role === "user" ? "You" : "Bot"}:</b> {m.content}
            </div>
          ))}
          {loading && <div className="opacity-60">Bot is typing…</div>}
        </div>

        <div className="flex flex-col gap-4">
          <MemoryPeek baseUrl={baseUrl} />
          <RecentMessages baseUrl={baseUrl} />
        </div>
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 border rounded px-3 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Say hi…"
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="border rounded px-4" onClick={send} disabled={loading}>Send</button>
      </div>
    </div>
  );
}
