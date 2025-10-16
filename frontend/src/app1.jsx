import { useState, useRef, useEffect } from 'react'
import './App.css'

// Replace with your actual Lambda URL
const LAMBDA_URL = import.meta.env.VITE_LAMBDA_URL || 'YOUR_LAMBDA_URL_HERE'

function App() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: "Hi! I'm your step-by-step AI tutor. Ask anything and I'll explain it clearly.\n\n¡Hola! Soy tu tutor de IA paso a paso. Pregunta lo que quieras y te lo explicaré claramente.\n\n🌍 I automatically respond in your language! / ¡Respondo automáticamente en tu idioma!",
      timestamp: new Date().toISOString()
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (e) => {
    e.preventDefault()
    
    if (!input.trim() || isLoading) return

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      console.log('🚀 Sending request to:', LAMBDA_URL)
      console.log('📝 Query:', input.trim())

      const response = await fetch(LAMBDA_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: input.trim()  // Lambda expects 'prompt'
        })
      })

      console.log('📥 Response status:', response.status)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || errorData.message || `HTTP ${response.status}`)
      }

      const data = await response.json()
      console.log('✅ Response data:', data)

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        language: data.language || 'en',  // Get detected language
        metadata: data.metadata || {},
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, assistantMessage])

    } catch (error) {
      console.error('❌ Error:', error)
      
      const errorMessage = {
        id: Date.now() + 1,
        role: 'error',
        content: `Error: ${error.message}. Please check:\n• Lambda URL is correct\n• Lambda is deployed and running\n• API Gateway trigger is configured\n• CORS is enabled`,
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-icon">🧠</span>
            <h1>Smart Study Buddy</h1>
          </div>
          <p className="subtitle">Your step-by-step AI tutor.</p>
          <p className="tech-stack">
            Ask any question. Get a clear, structured explanation fast. 
            Built on AWS Bedrock (Claude 3.5 Sonnet v2).
            <br />
            🌍 <strong>Bilingual:</strong> Automatically responds in English or Spanish!
          </p>
        </div>
      </header>

      {/* Chat Messages */}
      <main className="chat-container">
        <div className="messages-area">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          
          {isLoading && (
            <div className="message assistant-message">
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <p className="loading-text">Searching and analyzing...</p>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={sendMessage} className="input-form">
          <div className="input-wrapper">
            <button type="button" className="attach-btn" title="Coming soon">
              <span>+</span>
            </button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              disabled={isLoading}
              className="message-input"
            />
            <button 
              type="submit" 
              disabled={isLoading || !input.trim()}
              className="send-btn"
            >
              Ask
            </button>
          </div>
        </form>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>© 2025 — Built with <strong>AWS Bedrock</strong> · Frontend: <strong>React</strong></p>
      </footer>
    </div>
  )
}

// Message Bubble Component
function MessageBubble({ message }) {
  const { role, content, sources, metadata, language } = message

  return (
    <div className={`message ${role}-message`}>
      <div className="message-avatar">
        {role === 'user' ? '👤' : role === 'error' ? '⚠️' : '🤖'}
      </div>
      <div className="message-content">
        {/* Language indicator for assistant messages */}
        {role === 'assistant' && language && (
          <div className="language-badge">
            {language === 'es' ? '🇪🇸 Español' : '🇬🇧 English'}
          </div>
        )}
        
        <div className="message-text">{content}</div>
        
        {/* Show sources if available */}
        {sources && sources.length > 0 && (
          <div className="sources-section">
            <h4>📚 {language === 'es' ? 'Fuentes:' : 'Sources:'}</h4>
            <ul>
              {sources.map((source, idx) => (
                <li key={idx}>
                  <a href={source.url} target="_blank" rel="noopener noreferrer">
                    {source.type === 'news' && '📰 '}
                    {source.title}
                    {source.source && ` (${source.source})`}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Show metadata if available */}
        {metadata && (metadata.web_sources_found > 0 || metadata.news_articles_found > 0) && (
          <div className="metadata">
            <small>
              {metadata.web_sources_found} web sources · {metadata.news_articles_found} news articles
            </small>
          </div>
        )}
      </div>
    </div>
  )
}

export default App

