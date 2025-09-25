import { useEffect, useRef, useState } from 'react';
import { clsx } from 'clsx';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const timestamp = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

const bubbleStyles = {
  user: 'bg-tcfd-sky text-slate-900 self-end',
  assistant: 'bg-white text-slate-900 self-start',
};

function SourceList({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <details className="mt-3 text-sm text-slate-600">
      <summary className="cursor-pointer font-semibold text-tcfd-navy">Sources</summary>
      <ul className="mt-2 space-y-2">
        {sources.map((source, index) => (
          <li key={`${source.file}-${index}`} className="rounded bg-slate-100 p-2">
            <p className="font-medium text-sm text-slate-700">{source.file}</p>
            <p className="text-xs text-slate-500">{source.snippet}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}

export default function ChatPanel({ mode, title, description, endpoint }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const outgoing = {
      role: 'user',
      content: trimmed,
      time: timestamp(),
    };

    const history = [...messages, outgoing];
    setMessages(history);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const payloadMessages = history.map(({ role, content }) => ({
        role,
        content,
      }));

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: null,
          messages: payloadMessages,
        }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || 'Request failed');
      }

      const data = await response.json();

      const assistantMsg = {
        role: 'assistant',
        content: data.response,
        time: timestamp(),
        sources: data.sources ?? [],
      };

      setMessages(current => [...current, assistantMsg]);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4">
        <h2 className="text-2xl font-semibold text-tcfd-navy">{title}</h2>
        <p className="text-sm text-slate-600">{description}</p>
      </div>

      <div className="flex-1 overflow-y-auto rounded-xl bg-white p-4 shadow-card">
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={clsx(
              'mb-4 max-w-xl rounded-xl px-4 py-3 shadow-sm transition-all',
              bubbleStyles[message.role] ?? bubbleStyles.assistant
            )}
          >
            <div className="mb-1 text-xs uppercase tracking-wide text-slate-500">
              {message.role === 'user' ? 'You' : 'Assistant'} • {message.time}
            </div>
            <ReactMarkdown
              className="prose prose-sm max-w-none text-sm leading-relaxed"
              components={{
                a: ({ href, children, ...props }) => (
                  <a
                    href={href}
                    className="font-semibold text-blue-600 no-underline hover:underline"
                    target="_blank"
                    rel="noopener noreferrer"
                    {...props}
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
            <SourceList sources={message.sources} />
          </div>
        ))}
        {loading && (
          <div className="self-start rounded-xl bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
            Assistant is thinking...
          </div>
        )}
        <div ref={endRef} />
      </div>

      {error && (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="mt-4 flex gap-2">
        <textarea
          className="flex-1 resize-none rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow focus:border-tcfd-sky focus:outline-none focus:ring-2 focus:ring-tcfd-sky/40"
          value={input}
          onChange={event => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
          placeholder={loading ? 'Waiting for response...' : 'Ask a question...'}
        />
        <button
          className="min-w-[120px] rounded-lg bg-tcfd-orange px-4 py-2 text-sm font-semibold text-white shadow hover:bg-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-200 disabled:cursor-not-allowed disabled:bg-orange-300"
          onClick={sendMessage}
          disabled={loading || !input.trim()}
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
