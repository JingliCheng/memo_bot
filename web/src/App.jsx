import { useState, useRef } from "react";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const controllerRef = useRef(null);

  async function send() {
    if (!input.trim() || loading) return;
    setLoading(true);
    const userMsg = { role: "user", content: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");

    controllerRef.current = new AbortController();
    const resp = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controllerRef.current.signal,
      body: JSON.stringify({ message: userMsg.content }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let assistant = { role: "assistant", content: "" };
    setMessages((m) => [...m, assistant]);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      // SSE chunks look like: data:... \n\n
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
        } catch {
          // ignore parse errors for now
        }
      }
    }
    setLoading(false);
  }

  return (
    <div className="p-6 max-w-2xl mx-auto font-sans">
      <h1 className="text-2xl font-bold mb-4">AI Companion (MVP)</h1>
      <div className="border rounded p-3 h-96 overflow-auto mb-3 bg-white">
        {messages.map((m, i) => (
          <div key={i} className="mb-2">
            <b>{m.role === "user" ? "You" : "Bot"}:</b> {m.content}
          </div>
        ))}
        {loading && <div className="opacity-60">Bot is typing…</div>}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 border rounded px-3 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Say hi…"
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="border rounded px-4" onClick={send}>Send</button>
      </div>
    </div>
  );
}
