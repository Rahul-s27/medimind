import React, { useState, useRef, useEffect } from 'react';
import './ChatAgent.css';

const API_BASE_URL = 'http://localhost:8000';


// Reusable card to render structured AI responses
function AIAnswer({ data, showRaw }) {
  if (!data) return null;
  const title = data.title || 'AI Response';
  const summary = data.summary || '';
  const points = Array.isArray(data.points) ? data.points : [];
  const sources = Array.isArray(data.sources) ? data.sources : [];
  return (
    <div className="ai-card">
      {title && <h4 className="ai-card-title">{title}</h4>}
      {summary && <p className="ai-card-summary">{summary}</p>}
      {points.length > 0 && (
        <ul className="ai-card-points">
          {points.map((p, i) => (
            <li key={i}>{p}</li>
          ))}
        </ul>
      )}
      {sources.length > 0 && (
        <div className="ai-card-sources">
          <h5>Sources</h5>
          <ul>
            {sources.map((s, i) => (
              <li key={i}>
                <a href={(s.url || s.link) || '#'} target="_blank" rel="noopener noreferrer">
                  {s.title || s.name || 'Source'}
                </a>
                {showRaw && (s.raw_content || s.snippet) && (
                  <p className="raw-excerpt">{s.raw_content || s.snippet}</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function ChatAgent({ user, onLogout }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [models, setModels] = useState([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  // Set DeepSeek Chat V3 as default for web mode, fallback to openrouter/auto for AI mode
  const [selectedModel, setSelectedModel] = useState('deepseek/deepseek-chat-v3-0324:free');
  const [mode, setMode] = useState('web'); // 'ai' or 'web'
  const [uploadedFile, setUploadedFile] = useState(null);
  const [showSources, setShowSources] = useState(true);
  const [showRaw, setShowRaw] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Helper: display-friendly model name
  const formatModelLabel = (id) => {
    try {
      const afterSlash = id.split('/').pop() || id;
      const beforeColon = afterSlash.split(':')[0];
      return beforeColon
        .replace(/[-_]/g, ' ')
        .replace(/\b([a-z])/g, (m) => m.toUpperCase());
    } catch {
      return id;
    }
  };

  // Fetch available models from backend
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/models`);
        const data = await response.json();
        // Always include deepseek/deepseek-chat-v3-0324:free if missing
        let updatedModels = Array.isArray(data.models) ? [...data.models] : [];
        if (!updatedModels.includes('deepseek/deepseek-chat-v3-0324:free')) {
          updatedModels.unshift('deepseek/deepseek-chat-v3-0324:free');
        }
        setModels(updatedModels);
        // Preserve current selection if valid; otherwise prefer DeepSeek Chat V3, then auto
        setSelectedModel((prev) => {
          if (updatedModels.includes(prev)) return prev;
          if (updatedModels.includes('deepseek/deepseek-chat-v3-0324:free')) return 'deepseek/deepseek-chat-v3-0324:free';
          if (updatedModels.includes('openrouter/auto')) return 'openrouter/auto';
          return updatedModels[0] || prev;
        });
      } catch (error) {
        console.error('Failed to fetch models:', error);
        // Set default models if fetch fails
        const defaultModels = [
          'deepseek/deepseek-chat-v3-0324:free',
          'moonshotai/kimi-vl-a3b-thinking:free',
          'openrouter/auto',
          'qwen/qwen2.5-vl-32b-instruct:free',
          'nvidia/llama-3.1-nemotron-ultra-253b-v1:free'
        ];
        setModels(defaultModels);
        setSelectedModel('deepseek/deepseek-chat-v3-0324:free');
      }
    };
    
    fetchModels();
  }, []);

  // Partition models for AI vs Web modes using existing curated list
  const aiModelIds = React.useMemo(() => {
    // Prefer deep reasoning and vision-capable for AI mode
    return models.filter((m) => (
      m === 'deepseek/deepseek-chat-v3-0324:free' ||
      m === 'nvidia/llama-3.1-nemotron-ultra-253b-v1:free' ||
      m === 'qwen/qwen2.5-vl-32b-instruct:free' ||
      m === 'moonshotai/kimi-vl-a3b-thinking:free'
    ));
  }, [models]);

  const webModelIds = React.useMemo(() => {
    // Allow web mode to use the same curated set plus auto fallback
    return models.filter((m) => (
      m === 'openrouter/auto' ||
      m === 'deepseek/deepseek-chat-v3-0324:free' ||
      m === 'nvidia/llama-3.1-nemotron-ultra-253b-v1:free' ||
      m === 'qwen/qwen2.5-vl-32b-instruct:free'
    ));
  }, [models]);

  const visibleModels = mode === 'ai' ? aiModelIds : webModelIds;

  // When mode changes, ensure selectedModel belongs to the visible list
  useEffect(() => {
    if (!visibleModels.includes(selectedModel)) {
      if (visibleModels.length > 0) {
        setSelectedModel(visibleModels[0]);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, visibleModels.join('|')]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = {
      id: Date.now(),
      sender: 'user',
      content: input,
      timestamp: new Date(),
    };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput('');
    setIsTyping(true);
    
    // Send request to backend
    try {
      let response;
      if (mode === 'ai' && uploadedFile) {
        // Use multipart form to support image upload
        const form = new FormData();
        form.append('question', input);
        form.append('mode', mode);
        form.append('model', selectedModel);
        form.append('image', uploadedFile);
        response = await fetch(`${API_BASE_URL}/ask-form`, {
          method: 'POST',
          body: form,
        });
      } else {
        // JSON path for both AI (no file) and Web modes
        response = await fetch(`${API_BASE_URL}/ask`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: input,
            mode,
            model: selectedModel,
            max_tokens: 1200,
            temperature: 0.2,
          }),
        });
      }
      
      if (response.ok) {
        const data = await response.json();
        const isStructured = data && (data.title || data.summary || Array.isArray(data.points));
        const aiMsg = {
          id: Date.now() + 1,
          sender: 'ai',
          content: isStructured ? (data.answer || '') : (data.answer || "I'm here to help! Please describe your symptoms or question."),
          title: isStructured ? data.title : undefined,
          summary: isStructured ? data.summary : undefined,
          points: isStructured ? (Array.isArray(data.points) ? data.points : []) : undefined,
          sources: Array.isArray(data.sources) ? data.sources : [],
          timestamp: new Date(),
        };
        setMessages((msgs) => [...msgs, aiMsg]);
        // Keep file until user removes manually
      } else {
        // Handle error response
        setMessages((msgs) => [
          ...msgs,
          {
            id: Date.now() + 1,
            sender: 'ai',
            content: "Sorry, I encountered an error processing your request. Please try again.",
            timestamp: new Date(),
          },
        ]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((msgs) => [
        ...msgs,
        {
          id: Date.now() + 1,
          sender: 'ai',
          content: "Sorry, I'm having trouble connecting to the server. Please check your connection and try again.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const onFileChange = (e) => {
    const f = e.target.files && e.target.files[0] ? e.target.files[0] : null;
    setUploadedFile(f);
  };

  const removeFile = () => {
    setUploadedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Model details for sidebar
  const modelSpecs = {
    'deepseek/deepseek-chat-v3-0324:free': {
      name: 'DeepSeek Chat V3 (0324)',
      desc: 'Strong, balanced chat model with coherent reasoning. Great default for medical Q&A with quick, reliable responses.',
      strengths: 'Reasoning, speed, coherence',
      use: 'General medical Q&A, summaries, follow-ups',
    },
    'google/gemma-3-4b-it:free': {
      name: 'Google Gemma 3 4B IT',
      desc: 'Fast, efficient, and safe for general healthcare Q&A. Great for concise answers and low-latency needs.',
      strengths: 'Speed, safety, general medical knowledge',
      use: 'Quick triage, general advice, simple queries',
    },
    'meta-llama/llama-3.2-11b-vision-instruct:free': {
      name: 'Meta Llama 3.2 11B Vision',
      desc: 'Large multimodal model. Handles text and basic image input. Strong reasoning and broad medical coverage.',
      strengths: 'Reasoning, multimodal, broad medical',
      use: 'Complex cases, image+text, nuanced questions',
    },
    'moonshotai/kimi-vl-a3b-thinking:free': {
      name: 'Moonshot Kimi VL A3B',
      desc: 'Balanced generalist with good medical grounding. Handles longer context and nuanced topics.',
      strengths: 'Context length, nuance, reliability',
      use: 'Follow-up, multi-turn, detailed queries',
    },
    'openrouter/auto': {
      name: 'Auto (Best Free)',
      desc: 'Automatically selects the best free model. Good default for most users.',
      strengths: 'Simplicity, fallback',
      use: 'General use, unsure which to pick',
    },
    'qwen/qwen2.5-vl-32b-instruct:free': {
      name: 'Qwen 2.5 VL 32B Instruct',
      desc: 'Very large vision-language model. Excels at complex medical reasoning and multimodal tasks.',
      strengths: 'Complex reasoning, vision+text, depth',
      use: 'Advanced diagnosis, research, image+text',
    },
  };

  return (
    <div className={`chat-agent-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
      <main className="chat-agent-main">
        <header className="chat-agent-header">
          <button
            className="hamburger-button"
            aria-label="Toggle menu"
            onClick={() => setIsSidebarOpen((v) => !v)}
          >
            ☰
          </button>
          <div className="chat-agent-toggles">
            <label>
              <input type="checkbox" checked={showSources} onChange={() => setShowSources(!showSources)} />
              Show sources
            </label>
            <label>
              <input type="checkbox" checked={showRaw} onChange={() => setShowRaw(!showRaw)} />
              Show raw excerpts
            </label>
          </div>
          <div className="mode-selector-container">
            <div className={`mode-switch ${mode === 'ai' ? 'ai-active' : 'web-active'}`}>
              <button onClick={() => setMode('web')} className={mode === 'web' ? 'active' : ''}>Web</button>
              <button onClick={() => setMode('ai')} className={mode === 'ai' ? 'active' : ''}>AI</button>
            </div>
          </div>
          <div className="user-profile-section">
            <img src={user.picture} alt={user.name} className="user-avatar" />
            <span className="user-name">{user.name}</span>
            <button onClick={onLogout} className="logout-button">Logout</button>
          </div>
          <div className="chat-agent-model-selector">
            <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
              {visibleModels.map((model) => (
                <option key={model} value={model}>
                  {modelSpecs[model]?.name || formatModelLabel(model)}
                </option>
              ))}
            </select>
          </div>
        </header>

        <div className="messages-container">
          {messages.map((msg) => (
            <div key={msg.id} className={`message ${msg.sender}`}>
               <div className="message-avatar">
                {msg.sender === 'ai' ? (
                  <span className="ai-avatar">AI</span>
                ) : (
                  user && <img src={user.picture} alt="me" />
                )}
              </div>
              <div className="message-body">
                <div className="message-content">
                  {msg.sender === 'ai' && (msg.title || msg.summary || (Array.isArray(msg.points) && msg.points.length > 0)) ? (
                    <AIAnswer data={{ title: msg.title, summary: msg.summary, points: msg.points, sources: msg.sources }} showRaw={showRaw} />
                  ) : (
                    <span>{String(msg.content || '')}</span>
                  )}
                </div>
                {msg.sender === 'ai' && showSources && (!msg.title && !msg.summary && !(Array.isArray(msg.points) && msg.points.length > 0)) && msg.sources && msg.sources.length > 0 && (
                  <div className="sources-container">
                    <h4>Sources:</h4>
                    <ul>
                      {msg.sources.map((source, i) => (
                        <li key={i}>
                          <a href={source.url} target="_blank" rel="noopener noreferrer">
                            {source.title}
                          </a>
                          {showRaw && <p className="raw-excerpt">{source.raw_content}</p>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <span className="timestamp">{new Date(msg.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="message ai typing-indicator">
               <div className="message-avatar"><span className="ai-avatar">AI</span></div>
               <div className="message-body">
                <div className="message-content">
                    <span className="dot"></span><span className="dot"></span><span className="dot"></span>
                  </div>
                </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <footer className="input-form-container">
          {uploadedFile && (
            <div className="file-chip-container">
              <span className="file-chip" title={uploadedFile.name}>
                <span className="file-name">{uploadedFile.name}</span>
                <button type="button" className="file-remove" onClick={removeFile} aria-label="Remove file">×</button>
              </span>
            </div>
          )}
          <div className="chat-agent-input-form">
            <div className="file-upload-bottom-wrap">
              <button type="button" className="file-upload-btn" onClick={() => fileInputRef.current && fileInputRef.current.click()}>
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
              </button>
              <input ref={fileInputRef} type="file" accept="image/*" onChange={onFileChange} style={{ display: 'none' }} />
            </div>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }}}
              placeholder="Ask a question..."
              rows="1"
            />
            <button onClick={sendMessage} disabled={!input.trim() || isTyping}>
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
          </div>
        </footer>
      </main>

      {isSidebarOpen && <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)} />}

      <aside className="chat-agent-sidebar">
        <h3>Model Details</h3>
        <div className="sidebar-content">
          {models.map((model) => (
            <div key={model} className="model-spec-item">
              <h4>{modelSpecs[model]?.name || formatModelLabel(model)}</h4>
              <p>{modelSpecs[model]?.desc}</p>
              <ul>
                <li><strong>Strengths:</strong> {modelSpecs[model]?.strengths}</li>
                <li><strong>Best for:</strong> {modelSpecs[model]?.use}</li>
              </ul>
            </div>
          ))}
        </div>
        <div className="sidebar-footer">
          <span>Choose a model based on your needs.<br />All models are free to use.</span>
        </div>
      </aside>
    </div>
  );
}