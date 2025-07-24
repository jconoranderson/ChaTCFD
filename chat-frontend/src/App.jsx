import { useState, useEffect, useRef } from 'react';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messageEndRef = useRef(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const newMessages = [...messages, { role: 'user', content: input }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'tcfd-mistral',
          messages: newMessages,
        }),
      });

      const data = await response.json();
      const reply = { role: 'assistant', content: data.response };
      setMessages([...newMessages, reply]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="max-w-3xl mx-auto p-4 h-screen flex flex-col">
      <h1 className="text-3xl font-bold mb-4">ChatTCFD</h1>
      <div className="flex-1 overflow-y-auto bg-gray-100 p-4 rounded space-y-2">
        {messages.filter(m => m.role !== 'system').map((msg, idx) => (
          <div key={idx} className={`p-3 rounded ${msg.role === 'user' ? 'bg-white text-right' : 'bg-blue-100 text-left'}`}>
            <strong>{msg.role === 'user' ? 'You' : 'Assistant'}:</strong> {msg.content}
          </div>
        ))}
        <div ref={messageEndRef} />
      </div>
      <div className="mt-4 flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1 p-2 border rounded"
          rows={2}
          placeholder="Type your message..."
        />
        <button onClick={sendMessage} disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded">
          {loading ? 'Thinking...' : 'Send'}
        </button>
      </div>
    </div>
  );
}

export default App;
