import { useEffect, useRef, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL; // keep your .env with VITE_API_URL

export default function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([
    { role: "ai", text: "Hi! I’m your step-by-step AI tutor. Ask anything and I’ll explain it clearly." }
  ]);

  const scrollRef = useRef(null);

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    const prompt = input.trim();
    if (!prompt) return;

    // Push user message to the right
    setMessages(prev => [...prev, { role: "user", text: prompt }]);
    setInput("");

    try {
      // Call your Lambda URL (expects { answer: "..." } JSON)
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
      });

      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status} – ${t}`);
      }

      const data = await res.json();
      const answer =
        typeof data === "string"
          ? data
          : data.answer ?? data.output?.content?.[0]?.text ?? "Sorry, I couldn’t parse the answer.";

      // Push AI message to the left
      setMessages(prev => [...prev, { role: "ai", text: answer }]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: "ai", text: `⚠️ Error: ${err.message}` }
      ]);
    }
  }

  return (
    <div className="container">
      {/* Top badge */}
      <div className="badge" aria-label="Smart Study Buddy">
        <span style={{ width: 8, height: 8, borderRadius: 999, background: "#7dd3fc" }} />
        Smart Study Buddy
      </div>

      {/* Heading */}
      <h1 class="h">
        Your step-by-step <span class="grad">AI tutor</span><span class="punct">.</span>
      </h1>
      <p className="sub">
        Ask any question. Get a clear, structured explanation — fast. Built on AWS Bedrock (Claude 3.5 Sonnet v2).
      </p>

      {/* Chat card */}
      <div className="chat-card">
        {/* Scroll area */}
        <div ref={scrollRef} className="chat-scroll" id="chatScroll">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`msg-row ${m.role === "user" ? "msg--user" : "msg--ai"}`}
            >
              <div className="bubble">{m.text}</div>
            </div>
          ))}
        </div>

        {/* Composer */}
        <form className="composer" onSubmit={handleSend}>
          <input
            className="input"
            placeholder="Type your message…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            aria-label="Message"
          />
          <button className="send" type="submit">Ask</button>
        </form>
      </div>

      {/* Footer */}
      <p className="footer">
        Built with <strong>AWS Bedrock</strong> • Frontend: <strong>React</strong> • 2025
      </p>
    </div>
  );
}







