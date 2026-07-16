import { useState, useRef, useEffect } from 'react'

const STREAM_URL = 'http://localhost:8003/chat/stream'

export default function App() {
  const [messages, setMessages]   = useState([])
  const [activity, setActivity]   = useState([])
  const [loading, setLoading]     = useState(false)
  const [input, setInput]         = useState('')
  const sessionId = useRef(crypto.randomUUID())
  const chatEndRef = useRef(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage() {
    if (!input.trim() || loading) return

    const userMsg = input.trim()
    setInput('')
    setLoading(true)
    setActivity([])

    // add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])

    // add empty assistant message (we'll update it as stream arrives)
    setMessages(prev => [...prev, { role: 'assistant', content: '⏳ Thinking...' }])

    try {
      const response = await fetch(STREAM_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, session_id: sessionId.current })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n').filter(l => l.trim())

        for (const line of lines) {
          const chunk = JSON.parse(line)

          if (chunk.type === 'status') {
            setActivity(prev => [...prev, chunk.content])
          } else if (chunk.type === 'result') {
            // replace the last "Thinking..." message with the real answer
            setMessages(prev => [
              ...prev.slice(0, -1),
              { role: 'assistant', content: chunk.content }
            ])
          } else if (chunk.type === 'structured_data') {
            setMessages(prev => {
              const last = prev[prev.length - 1];
              return [
                ...prev.slice(0, -1),
                { ...last, hotels: chunk.hotels || [], flights: chunk.flights || [] }
              ]
            })
          }
        }
      }
    } catch (err) {
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: `⚠️ Error: ${err.message}` }
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <span className="logo">✈️ TripWeaver</span>
        <span className="tagline">Your AI Travel Assistant</span>
      </header>

      <main className="main">
        <section className="chat-section">
          <div className="chat-window">
            {messages.length === 0 && (
              <div className="empty-state">
                <h2>🌍 Ready for your next adventure?</h2>
                <p>I can help you search and book flights and hotels. Where would you like to go?</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="bubble">
                  {msg.content}
                  
                  {msg.flights?.length > 0 && (
                    <div className="result-cards flights">
                      <h4>✈️ Flight Options</h4>
                      <div className="card-container">
                      {msg.flights.map((f, i) => (
                        <div key={i} className="result-card" onClick={() => setInput(`book flight ${f.id} for Jane`)}>
                          <div className="card-header">
                            <span className="airline">{f.airline || 'Standard Air'}</span>
                            <span className="price">${f.price}</span>
                          </div>
                          <div className="card-body">
                            <div>From: <strong>{f.origin}</strong></div>
                            <div>To: <strong>{f.destination}</strong></div>
                            <div className="card-id">ID: {f.id}</div>
                          </div>
                        </div>
                      ))}
                      </div>
                    </div>
                  )}

                  {msg.hotels?.length > 0 && (
                    <div className="result-cards hotels">
                      <h4>🏨 Hotel Options</h4>
                      <div className="card-container">
                      {msg.hotels.map((h, i) => (
                        <div key={i} className="result-card" onClick={() => setInput(`book hotel ${h.id} for Jane`)}>
                          <div className="card-header">
                            <span className="hotel-name">{h.name}</span>
                            <span className="price">${h.price}/night</span>
                          </div>
                          <div className="card-body">
                            <div>⭐ {h.starRating || h.stars} Star</div>
                            <div>City: {h.city}</div>
                            <div className="rooms">Available rooms: {h.availableRooms || 0}</div>
                          </div>
                        </div>
                      ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div className="quick-replies">
            {['Find 5-star hotels in Mumbai', 'Plan a trip to Paris from London', 'Are there any cheaper options?'].map(txt => (
              <button key={txt} className="quick-btn" onClick={() => {setInput(txt)}}>{txt}</button>
            ))}
          </div>

          <div className="input-bar">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              placeholder="Ask about flights, hotels, or travel plans..."
            />
            <button onClick={sendMessage} disabled={loading}>
              {loading ? '⏳' : 'Send ✈️'}
            </button>
          </div>
        </section>

        <aside className="activity-panel">
          <h3>⚡ Agent Activity</h3>
          {activity.length === 0 && !loading && (
            <p className="empty-activity">Activity will appear here when you send a message.</p>
          )}
          {activity.map((line, i) => (
            <div key={i} className="activity-item">✔ {line}</div>
          ))}
          {loading && <div className="activity-item pulse">⏳ Working...</div>}
        </aside>
      </main>
    </div>
  )
}