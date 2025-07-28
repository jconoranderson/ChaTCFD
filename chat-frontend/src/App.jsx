import { useState, useRef, useEffect } from "react";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  // Scroll to bottom when messages update
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const formatTime = () =>
    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  // Streaming effect for model response
  const streamMessage = (text, sources) => {
    let index = 0;
    const interval = setInterval(() => {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === "model" && last.streaming) {
          return [
            ...prev.slice(0, -1),
            { ...last, content: text.slice(0, index), sources },
          ];
        } else {
          return [...prev, { role: "model", content: "", streaming: true, sources }];
        }
      });

      index++;
      if (index > text.length) {
        clearInterval(interval);
        setMessages((prev) =>
          prev.map((m, i) =>
            i === prev.length - 1 ? { ...m, streaming: false } : m
          )
        );
      }
    }, 15);
  };

  const sendMessage = async () => {
    if (!input) return;

    const newMessages = [
      ...messages,
      { role: "user", content: input, time: formatTime() },
    ];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "tcfd-mistral",
          messages: newMessages.map(({ role, content }) => ({ role, content })),
        }),
      });

      const data = await res.json();
      streamMessage(data.response, data.sources || []);
    } catch (err) {
      console.error("API Error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    // Orange page background
    <div
      className="flex items-center justify-center h-screen p-4"
      style={{ backgroundColor: "#F48120" }}
    >
      {/* Chat Container */}
      <div className="flex flex-col w-full max-w-3xl h-full max-h-[90vh] bg-white border border-gray-300 rounded-lg shadow-md overflow-hidden">
        {/* Header */}
        <header className="flex items-center px-4 py-2 bg-white border-b">
          <img src="/tcfd.jpg" alt="Logo" className="h-8 mr-2 rounded" />
          <h1 className="text-xl font-bold text-gray-800">ChaTCFD</h1>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`max-w-lg px-4 py-2 rounded-lg ${
                msg.role === "user"
                  ? "bg-blue-500 text-white self-end ml-auto"
                  : "bg-gray-200 text-gray-900 self-start"
              }`}
            >
              <div className="text-xs text-gray-600 mb-1">
                {msg.role === "user" ? "You" : "Assistant"} • {msg.time}
              </div>
              <div>{msg.content}</div>

              {/* Source citations */}
              {msg.sources && msg.sources.length > 0 && (
                <details className="mt-2 text-xs">
                  <summary className="cursor-pointer text-blue-500">
                    Sources
                  </summary>
                  <ul className="list-disc ml-4">
                    {msg.sources.map((s, idx) => (
                      <li key={idx}>
                        {s.file}: <span className="text-gray-600">{s.snippet}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          ))}

          {/* Typing indicator */}
          {loading && (
            <div className="max-w-lg px-4 py-2 rounded-lg bg-gray-200 text-gray-500">
              Model is thinking<span className="animate-pulse">...</span>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 bg-white border-t flex">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 border rounded-lg px-3 py-2 focus:outline-none focus:ring focus:border-blue-300"
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          />
          <button
            onClick={sendMessage}
            className="ml-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
