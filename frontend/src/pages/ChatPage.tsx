import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Send, Plus, Trash2, AlertTriangle, AlertCircle, Info, CheckCircle,
  ChevronDown, Bot, User, Mic, MicOff, Volume2, VolumeX
} from 'lucide-react'
import { chatApi } from '../api/chat'
import type { Conversation, ConversationDetail, Message } from '../types'
import { format } from 'date-fns'
import clsx from 'clsx'
import ReactMarkdown from 'react-markdown'

const ESCALATION_CONFIG = {
  none: { color: 'bg-green-50 border-green-200 text-green-800', icon: CheckCircle, label: 'No concern' },
  mild: { color: 'bg-blue-50 border-blue-200 text-blue-800', icon: Info, label: 'Mild concern' },
  urgent: { color: 'bg-orange-50 border-orange-200 text-orange-800', icon: AlertCircle, label: 'See a doctor soon' },
  emergency: { color: 'bg-red-50 border-red-200 text-red-800', icon: AlertTriangle, label: 'SEEK EMERGENCY CARE' },
}

const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

export default function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const navigate = useNavigate()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConv, setActiveConv] = useState<ConversationDetail | null>(null)
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [speaking, setSpeaking] = useState(false)

  // Voice mode state
  const [voiceMode, setVoiceMode] = useState(false)
  const [listening, setListening] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle')
  const recognitionRef = useRef<any>(null)
  const voiceModeRef = useRef(false) // ref to avoid stale closures
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => { loadConversations() }, [])
  useEffect(() => { if (conversationId) loadConversation(conversationId) }, [conversationId])
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [activeConv?.messages, streamingText])

  const loadConversations = async () => {
    const { data } = await chatApi.listConversations()
    setConversations(data.items)
  }

  const loadConversation = async (id: string) => {
    const { data } = await chatApi.getConversation(id)
    setActiveConv(data)
  }

  const newConversation = async () => {
    const { data } = await chatApi.createConversation()
    setConversations((prev) => [data, ...prev])
    navigate(`/chat/${data.id}`)
  }

  const deleteConversation = async (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    await chatApi.deleteConversation(id)
    setConversations((prev) => prev.filter((c) => c.id !== id))
    if (conversationId === id) {
      setActiveConv(null)
      navigate('/chat')
    }
  }

  const getDisplayText = (text: string) => {
    const idx = text.indexOf('\n---\n')
    return idx >= 0 ? text.substring(0, idx) : text
  }

  // ── Speak text using browser TTS ──
  const speakText = useCallback((text: string): Promise<void> => {
    return new Promise((resolve) => {
      window.speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 1.05
      utterance.pitch = 1.0
      utterance.onend = () => { setSpeaking(false); setVoiceStatus('idle'); resolve() }
      utterance.onerror = () => { setSpeaking(false); setVoiceStatus('idle'); resolve() }
      setSpeaking(true)
      setVoiceStatus('speaking')
      window.speechSynthesis.speak(utterance)
    })
  }, [])

  // ── Send message (used by both text and voice) ──
  const sendMessageText = useCallback(async (msg: string, autoSpeak = false) => {
    if (!msg.trim() || streaming || !conversationId) return

    setStreaming(true)
    setStreamingText('')

    const userMsg: Message = {
      id: Date.now().toString(), role: 'user', content: msg,
      escalation_level: null, confidence_score: null,
      recommendations: null, disclaimer: null, follow_up_questions: null,
      created_at: new Date().toISOString(),
    }
    setActiveConv((prev) => prev ? { ...prev, messages: [...prev.messages, userMsg] } : prev)

    if (autoSpeak) setVoiceStatus('thinking')

    let fullText = ''
    await chatApi.sendMessage(
      conversationId,
      msg,
      (chunk) => {
        fullText += chunk
        setStreamingText((prev) => prev + chunk)
      },
      async () => {
        setStreaming(false)
        setStreamingText('')
        await loadConversation(conversationId)
        loadConversations()

        if (autoSpeak && voiceModeRef.current) {
          // Strip follow-up section for speech
          const idx = fullText.indexOf('\n---\n')
          const answerText = idx >= 0 ? fullText.substring(0, idx) : fullText
          // Strip markdown for cleaner speech
          const cleanText = answerText.replace(/[*#_`>\[\]()]/g, '').replace(/\n+/g, '. ').trim()
          await speakText(cleanText)
          // Auto-listen again after speaking
          if (voiceModeRef.current) {
            startVoiceListening()
          }
        }
      },
      (err) => {
        console.error(err)
        setStreaming(false)
        setStreamingText('')
        setVoiceStatus('idle')
        // Retry listening on error in voice mode
        if (voiceModeRef.current) startVoiceListening()
      }
    )
  }, [conversationId, streaming, speakText])

  // ── Text input send ──
  const sendMessage = async () => {
    if (!input.trim()) return
    const msg = input.trim()
    setInput('')
    await sendMessageText(msg, false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const sendFollowUp = (question: string) => {
    sendMessageText(question, false)
  }

  // ── Voice mode: Alexa-style continuous conversation ──
  const startVoiceListening = useCallback(() => {
    if (!SpeechRecognition || !voiceModeRef.current) return

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onstart = () => {
      setListening(true)
      setVoiceStatus('listening')
    }

    recognition.onresult = (event: any) => {
      const transcript = event.results[0]?.[0]?.transcript?.trim()
      if (transcript) {
        sendMessageText(transcript, true)
      }
    }

    recognition.onend = () => {
      setListening(false)
      // If no result was captured and still in voice mode, restart
      // (handled by onresult sending message, which chains back)
    }

    recognition.onerror = (event: any) => {
      setListening(false)
      if (event.error === 'no-speech' && voiceModeRef.current) {
        // No speech detected, try again
        setTimeout(() => { if (voiceModeRef.current) startVoiceListening() }, 500)
      }
    }

    try {
      recognition.start()
      recognitionRef.current = recognition
    } catch {
      // Already started
    }
  }, [sendMessageText])

  const toggleVoiceMode = useCallback(async () => {
    if (voiceMode) {
      // Turn off
      voiceModeRef.current = false
      setVoiceMode(false)
      setVoiceStatus('idle')
      setListening(false)
      recognitionRef.current?.stop()
      recognitionRef.current = null
      window.speechSynthesis.cancel()
      setSpeaking(false)
    } else {
      // Turn on — create conversation if needed
      if (!conversationId) {
        const { data } = await chatApi.createConversation()
        setConversations((prev) => [data, ...prev])
        navigate(`/chat/${data.id}`)
        // Wait for navigation
        setTimeout(() => {
          voiceModeRef.current = true
          setVoiceMode(true)
          startVoiceListening()
        }, 300)
      } else {
        voiceModeRef.current = true
        setVoiceMode(true)
        startVoiceListening()
      }
    }
  }, [voiceMode, conversationId, startVoiceListening, navigate])

  // ── Single message TTS ──
  const playTTS = (text: string) => {
    if (speaking) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
      return
    }
    speakText(text)
  }

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="w-60 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-3 border-b border-gray-200">
          <button onClick={newConversation} className="btn-primary w-full flex items-center justify-center gap-2 text-sm py-2">
            <Plus className="w-4 h-4" /> New chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => navigate(`/chat/${conv.id}`)}
              className={clsx(
                'group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors',
                conv.id === conversationId ? 'bg-primary-50 text-primary-700' : 'hover:bg-gray-100 text-gray-700'
              )}
            >
              <span className="truncate flex-1">{conv.title || 'New conversation'}</span>
              <button
                onClick={(e) => deleteConversation(conv.id, e)}
                className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-500 transition-all"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        {!conversationId && !voiceMode ? (
          <EmptyState onNew={newConversation} onVoice={toggleVoiceMode} />
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {activeConv?.messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} onFollowUp={sendFollowUp} onPlayTTS={playTTS} speaking={speaking} />
              ))}

              {streaming && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-primary-600" />
                  </div>
                  <div className="flex-1 bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 max-w-2xl">
                    {streamingText ? (
                      <div className="text-sm text-gray-800 prose prose-sm max-w-none">
                        <ReactMarkdown>{getDisplayText(streamingText)}</ReactMarkdown>
                      </div>
                    ) : (
                      <div className="flex gap-1 py-1">
                        {[0, 1, 2].map((i) => (
                          <div key={i} className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Voice mode overlay */}
            {voiceMode && (
              <div className="absolute inset-0 bg-black/5 backdrop-blur-[1px] flex items-end justify-center pb-32 pointer-events-none z-10">
                <div className="pointer-events-auto flex flex-col items-center gap-4">
                  <div className={clsx(
                    'text-sm font-medium px-4 py-2 rounded-full',
                    voiceStatus === 'listening' && 'bg-red-100 text-red-700',
                    voiceStatus === 'thinking' && 'bg-yellow-100 text-yellow-700',
                    voiceStatus === 'speaking' && 'bg-blue-100 text-blue-700',
                    voiceStatus === 'idle' && 'bg-gray-100 text-gray-600',
                  )}>
                    {voiceStatus === 'listening' && 'Listening...'}
                    {voiceStatus === 'thinking' && 'Thinking...'}
                    {voiceStatus === 'speaking' && 'Speaking...'}
                    {voiceStatus === 'idle' && 'Voice mode active'}
                  </div>

                  {/* Pulsing mic button */}
                  <button
                    onClick={toggleVoiceMode}
                    className={clsx(
                      'w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-lg',
                      voiceStatus === 'listening'
                        ? 'bg-red-500 hover:bg-red-600 animate-pulse'
                        : voiceStatus === 'speaking'
                        ? 'bg-blue-500 hover:bg-blue-600'
                        : 'bg-primary-600 hover:bg-primary-700'
                    )}
                    title="Stop voice mode"
                  >
                    {voiceStatus === 'listening' ? (
                      <Mic className="w-8 h-8 text-white" />
                    ) : (
                      <MicOff className="w-8 h-8 text-white" />
                    )}
                  </button>
                  <p className="text-xs text-gray-500">Tap to end voice mode</p>
                </div>
              </div>
            )}

            {/* Input bar */}
            <div className="border-t border-gray-200 bg-white p-4 relative z-20">
              <div className="max-w-3xl mx-auto">
                <div className="flex gap-3 items-end">
                  <textarea
                    ref={textareaRef}
                    className="input flex-1 resize-none min-h-[44px] max-h-32"
                    placeholder="Describe your symptoms, ask about lab results..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    rows={1}
                    disabled={streaming || voiceMode}
                  />
                  <button
                    onClick={toggleVoiceMode}
                    className={clsx(
                      'px-4 py-2.5 flex items-center gap-2 rounded-lg transition-colors',
                      voiceMode
                        ? 'bg-red-500 hover:bg-red-600 text-white'
                        : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                    )}
                    disabled={streaming && !voiceMode}
                    title={voiceMode ? 'Stop voice mode' : 'Start voice conversation'}
                  >
                    {voiceMode ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={sendMessage}
                    className="btn-primary px-4 py-2.5 flex items-center gap-2"
                    disabled={!input.trim() || streaming || voiceMode}
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-2 text-center">
                  For emergencies, call 911. MedAgent is not a substitute for professional medical care.
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function MessageBubble({ message, onFollowUp, onPlayTTS, speaking }: {
  message: Message; onFollowUp?: (q: string) => void; onPlayTTS?: (text: string) => void; speaking?: boolean
}) {
  const isUser = message.role === 'user'
  const [showDetails, setShowDetails] = useState(false)
  const escalation = message.escalation_level
  const cfg = escalation ? ESCALATION_CONFIG[escalation as keyof typeof ESCALATION_CONFIG] : null

  return (
    <div className={clsx('flex gap-3', isUser && 'flex-row-reverse')}>
      <div className={clsx('w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0', isUser ? 'bg-primary-600' : 'bg-primary-100')}>
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-primary-600" />}
      </div>
      <div className={clsx('flex flex-col gap-2 max-w-2xl', isUser && 'items-end')}>
        <div className={clsx('px-4 py-3 rounded-2xl', isUser ? 'bg-primary-600 text-white rounded-tr-sm' : 'bg-white border border-gray-200 rounded-tl-sm text-gray-800')}>
          <div className={clsx('text-sm prose prose-sm max-w-none', isUser && 'prose-invert')}>
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>

        {!isUser && escalation && escalation !== 'none' && cfg && (
          <div className={clsx('flex items-center gap-2 px-3 py-2 rounded-lg border text-sm', cfg.color)}>
            <cfg.icon className="w-4 h-4 flex-shrink-0" />
            <span className="font-medium">{cfg.label}</span>
          </div>
        )}

        {!isUser && (message.recommendations?.length || message.disclaimer) && (
          <button onClick={() => setShowDetails(!showDetails)} className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700">
            Details <ChevronDown className={clsx('w-3 h-3 transition-transform', showDetails && 'rotate-180')} />
          </button>
        )}

        {!isUser && showDetails && (
          <div className="card p-3 text-sm space-y-2 w-full">
            {message.recommendations && message.recommendations.length > 0 && (
              <div>
                <p className="font-medium text-gray-700 mb-1">Recommendations</p>
                <ul className="space-y-1">
                  {message.recommendations.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-gray-600"><span className="text-primary-500 mt-0.5">•</span> {r}</li>
                  ))}
                </ul>
              </div>
            )}
            {message.confidence_score && <p className="text-gray-500 text-xs">Confidence: {Math.round(message.confidence_score * 100)}%</p>}
            {message.disclaimer && <p className="text-gray-400 text-xs italic border-t border-gray-100 pt-2">{message.disclaimer}</p>}
          </div>
        )}

        {!isUser && message.follow_up_questions && message.follow_up_questions.length > 0 && (
          <div className="flex flex-wrap gap-2 w-full">
            {message.follow_up_questions.map((q, i) => (
              <button key={i} onClick={() => onFollowUp?.(q)} className="text-xs bg-primary-50 text-primary-700 border border-primary-200 rounded-full px-3 py-1.5 hover:bg-primary-100 transition-colors text-left">
                {q}
              </button>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 px-1">
          <p className="text-xs text-gray-400">{format(new Date(message.created_at), 'HH:mm')}</p>
          {!isUser && onPlayTTS && (
            <button onClick={() => onPlayTTS(message.content)} className="text-gray-400 hover:text-primary-600 transition-colors" title={speaking ? 'Stop' : 'Read aloud'}>
              {speaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyState({ onNew, onVoice }: { onNew: () => void; onVoice: () => void }) {
  const suggestions = [
    'My blood pressure has been high lately, what does it mean?',
    'Explain my HbA1c result of 6.8%',
    'Is it safe to take ibuprofen with my current medications?',
    'I have a headache and mild fever for 2 days. Should I see a doctor?',
  ]
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
      <Bot className="w-12 h-12 text-primary-300 mb-4" />
      <h2 className="text-xl font-semibold text-gray-900 mb-2">Your personal health AI</h2>
      <p className="text-gray-500 mb-8 max-w-md">
        Ask about your symptoms, understand lab results, track medications, and get guidance on when to see a doctor.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl w-full mb-6">
        {suggestions.map((s) => (
          <button key={s} onClick={onNew} className="text-left text-sm bg-white border border-gray-200 rounded-xl px-4 py-3 hover:border-primary-300 hover:bg-primary-50 transition-colors text-gray-700">
            {s}
          </button>
        ))}
      </div>
      <div className="flex gap-3">
        <button onClick={onNew} className="btn-primary">Start chatting</button>
        <button onClick={onVoice} className="px-4 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg flex items-center gap-2 transition-colors">
          <Mic className="w-4 h-4" /> Voice conversation
        </button>
      </div>
    </div>
  )
}
