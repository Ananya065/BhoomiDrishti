import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api';

// BhoomiDrishti brand navy — matches --navy-800
const NAVY = '#16324f';

export default function CopilotWidget({ caseId }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Hi! I am the BhoomiDrishti Copilot. How can I assist you with this investigation?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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
      {/* ── Floating trigger button (always visible when panel is closed) ── */}
      {!isOpen && (
        <button
          aria-label="Open BhoomiDrishti Copilot"
          title="Open BhoomiDrishti Copilot"
          style={{
            position: 'fixed', bottom: 24, right: 24, zIndex: 9999,
            borderRadius: '50%', width: 56, height: 56,
            background: NAVY, color: '#fff', border: 'none',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(0,0,0,0.25)', cursor: 'pointer',
            fontSize: 13, fontWeight: 700, letterSpacing: '0.02em'
          }}
          onClick={() => setIsOpen(true)}
        >
          AI
        </button>
      )}

      {/* ── Chat panel ────────────────────────────────────────────────────── */}
      {isOpen && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, width: 370, height: 520,
          backgroundColor: '#fff', borderRadius: 12,
          boxShadow: '0 8px 32px rgba(0,0,0,0.22)',
          display: 'flex', flexDirection: 'column', zIndex: 9999,
          overflow: 'hidden', border: '1px solid #dde3ea'
        }}>

          {/* ── Header ────────────────────────────────────────────────────── */}
          <div style={{
            padding: '12px 16px',
            background: NAVY,
            color: '#fff',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexShrink: 0,
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <span style={{ fontWeight: 700, fontSize: 14, letterSpacing: '0.01em' }}>
                BhoomiDrishti Copilot
              </span>
              <span style={{ fontSize: 10.5, opacity: 0.75 }}>
                {caseId ? `Case mode · ${caseId}` : 'Global mode · All cases'}
              </span>
            </div>

            {/* ── Close button ─────────────────────────────────────────────── */}
            <button
              aria-label="Close Copilot"
              title="Close Copilot"
              onClick={() => setIsOpen(false)}
              style={{
                background: 'rgba(255,255,255,0.15)',
                border: '1px solid rgba(255,255,255,0.3)',
                color: '#fff',
                borderRadius: 6,
                width: 28,
                height: 28,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                fontSize: 18,
                lineHeight: 1,
                flexShrink: 0,
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.28)'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.15)'}
            >
              ×
            </button>
          </div>

          {/* ── Message list ──────────────────────────────────────────────── */}
          <div style={{
            flex: 1, overflowY: 'auto', padding: '14px 14px 8px',
            display: 'flex', flexDirection: 'column', gap: 12,
            backgroundColor: '#f3f5f8'
          }}>
            {messages.map((m, i) => (
              <div key={i} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '86%' }}>
                <div style={{
                  padding: '10px 14px',
                  // User: dark navy bg + white text. AI: white bg + dark text.
                  backgroundColor: m.role === 'user' ? NAVY : '#ffffff',
                  color: m.role === 'user' ? '#ffffff' : '#1a2433',
                  borderRadius: 12,
                  borderBottomRightRadius: m.role === 'user' ? 2 : 12,
                  borderBottomLeftRadius: m.role === 'user' ? 12 : 2,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                  fontSize: 13.5,
                  lineHeight: 1.45,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}>
                  {m.text}
                </div>
                {m.sources && m.sources.length > 0 && (
                  <div style={{ fontSize: 10, color: '#8a97a8', marginTop: 4, marginLeft: 4 }}>
                    Data sources: {m.sources.join(', ')}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div style={{
                alignSelf: 'flex-start', padding: '10px 14px',
                backgroundColor: '#fff', borderRadius: 12,
                fontSize: 13.5, color: '#8a97a8',
                boxShadow: '0 1px 3px rgba(0,0,0,0.08)'
              }}>
                Thinking…
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* ── Input bar ─────────────────────────────────────────────────── */}
          <div style={{
            padding: '10px 12px',
            borderTop: '1px solid #dde3ea',
            backgroundColor: '#fff',
            display: 'flex', gap: 8, flexShrink: 0
          }}>
            <input
              type="text"
              placeholder="Ask a question…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              style={{
                flex: 1, padding: '8px 12px',
                borderRadius: 6, border: '1px solid #c8d0db',
                fontSize: 13.5,
                color: '#1a2433',        /* dark text — always visible */
                backgroundColor: '#fff',
                outline: 'none',
              }}
            />
            <button
              onClick={sendMessage}
              disabled={loading}
              style={{
                padding: '8px 16px', background: NAVY,
                color: '#fff', border: 'none', borderRadius: 6,
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 13.5, fontWeight: 600,
                opacity: loading ? 0.6 : 1,
              }}
            >
              Send
            </button>
          </div>
        </div>
      )}
    </>
  );
}
