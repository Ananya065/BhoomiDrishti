import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api';

export default function CopilotWidget({ caseId }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Hi! I am the BhoomiDrishti Copilot. How can I assist you with this investigation?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [messages, isOpen]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setLoading(true);
    
    try {
      const res = await fetch('/api/copilot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, case_id: caseId })
      });
      const data = await res.json();
      
      setMessages(prev => [
        ...prev, 
        { 
          role: 'assistant', 
          text: data.reply || data.error || 'No response.',
          sources: data.sources || []
        }
      ]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', text: 'Failed to connect to Copilot API.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {!isOpen && (
        <button 
          className="btn primary" 
          style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 9999, borderRadius: '50%', width: 56, height: 56, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}
          onClick={() => setIsOpen(true)}
        >
          AI
        </button>
      )}

      {isOpen && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, width: 360, height: 500,
          backgroundColor: '#fff', borderRadius: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
          display: 'flex', flexDirection: 'column', zIndex: 9999, overflow: 'hidden', border: '1px solid var(--border)'
        }}>
          <div style={{ padding: '12px 16px', backgroundColor: 'var(--primary)', color: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600 }}>Groq Copilot {caseId ? '(Case Mode)' : '(Global Mode)'}</span>
            <button style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: 18 }} onClick={() => setIsOpen(false)}>×</button>
          </div>
          
          <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 12, backgroundColor: '#f9f9f9' }}>
            {messages.map((m, i) => (
              <div key={i} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
                <div style={{
                  padding: '10px 14px',
                  backgroundColor: m.role === 'user' ? 'var(--primary)' : '#fff',
                  color: m.role === 'user' ? '#fff' : 'var(--text)',
                  borderRadius: 12,
                  borderBottomRightRadius: m.role === 'user' ? 2 : 12,
                  borderBottomLeftRadius: m.role === 'user' ? 12 : 2,
                  boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                  fontSize: 14,
                  lineHeight: 1.4,
                  whiteSpace: 'pre-wrap'
                }}>
                  {m.text}
                </div>
                {m.sources && m.sources.length > 0 && (
                  <div style={{ fontSize: 10, color: 'var(--text-faint)', marginTop: 4, marginLeft: 4 }}>
                    Tools used: {m.sources.join(', ')}
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div style={{ alignSelf: 'flex-start', padding: '10px 14px', backgroundColor: '#fff', borderRadius: 12, fontSize: 14, color: 'var(--text-dim)' }}>
                Thinking...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div style={{ padding: 12, borderTop: '1px solid var(--border)', backgroundColor: '#fff', display: 'flex', gap: 8 }}>
            <input 
              type="text" 
              placeholder="Ask a question..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              style={{ flex: 1, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)', fontSize: 14 }}
            />
            <button className="btn primary" onClick={sendMessage} disabled={loading} style={{ padding: '8px 16px' }}>Send</button>
          </div>
        </div>
      )}
    </>
  );
}
