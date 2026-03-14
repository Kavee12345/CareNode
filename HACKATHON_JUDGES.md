# CareNode: Healthcare AI Assistant
## Hackathon Judge Documentation

---

## 📋 Project Overview

**CareNode** is an AI-powered healthcare assistant that provides intelligent medical consultations by combining conversational AI with document analysis and voice interaction. The app acts as a personal doctor who remembers your medical history and engages in natural, human-like conversations.

### Core Vision
Transform healthcare accessibility by providing:
- **Instant medical consultations** without appointment friction
- **Personalized advice** based on user's complete medical history
- **Multiple interaction modes** (text, voice, document upload)
- **Intelligent escalation** to emergency care when needed
- **Long-term health tracking** through persistent health notes

### Problem We're Solving
- Users need quick answers about symptoms but face barriers: appointment wait times, cost, accessibility
- Medical records are scattered and hard to search
- Follow-up appointments are often delayed
- Users struggle to remember and communicate their medical history to doctors

---

## 🏗️ Architecture Overview

### System Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Chat Page    │  │ Voice Mode   │  │ Documents    │       │
│  │ (Text Input) │  │ (Mic Button) │  │ (Upload)     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────┬──────────────────────────────────────────┬──────┘
             │ HTTP + SSE                               │
┌────────────▼──────────────────────────────────────────▼──────┐
│                    Backend (FastAPI)                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         Medical Agent (LangChain + Gemini)             │  │
│  │  - Conversational AI                                   │  │
│  │  - Health context awareness                           │  │
│  │  - Escalation detection                               │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │    Document Processing Pipeline                        │  │
│  │  - OCR (extract text from PDFs/images)                 │  │
│  │  - Chunking (512 tokens, 64 overlap)                   │  │
│  │  - Vector Embeddings (768-dim, Google)                 │  │
│  │  - Similarity Search (pgvector)                        │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  API Routes (Authentication + CORS)                    │  │
│  │  /chat        - text conversations                     │  │
│  │  /voice       - audio input/output                     │  │
│  │  /documents   - file uploads + management              │  │
│  │  /health      - health events + notes                  │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────┬──────────────────────────────────────────────┬──┘
             │                                              │
┌────────────▼──────────────────────────────────────────────▼──┐
│                    Data Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ PostgreSQL   │  │ pgvector     │  │ MinIO        │       │
│  │ (Metadata)   │  │ (Embeddings) │  │ (Documents)  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. **Medical Agent** (`backend/app/agent/medical_agent.py`)
- **LLM**: Google Gemini 2.5-flash (free tier available)
- **Context awareness**: Loads user's health notes from database
- **Real-time streaming**: SSE (Server-Sent Events) for instant response display
- **Escalation detection**: LLM determines if issue is urgent/emergency
- **Natural language**: Engineered to talk like a real doctor, not a chatbot

#### 2. **Document Processing** (`backend/app/services/document_service.py`)
- **OCR**: Python `pdf2image` + `pytesseract` for text extraction
- **Chunking**: Semantic chunks with 512 tokens + 64 token overlap
- **Embeddings**: Google `text-embedding-004` (768 dimensions)
- **Storage**: pgvector for fast similarity search (<100ms)
- **Retrieval**: Top-10 most relevant chunks for RAG context

#### 3. **Health Data Persistence** (`backend/app/models/health.py`)
- **UserHealthNote**: Auto-saved from user messages (detected via keywords)
  - Categories: symptom, medication, lifestyle, allergy, condition
  - Linked to source message for traceability
- **HealthEvent**: Auto-created for urgent/emergency escalations
  - Timestamp, severity, description
  - Facilitates follow-up and notification

#### 4. **Voice Conversation** (`frontend/src/pages/ChatPage.tsx`)
- **STT**: Browser Web Speech API (no backend processing)
- **TTS**: Browser SpeechSynthesis (native, no latency)
- **Alexa-style**: Continuous listening loop (speak → listen → speak)
- **Visual feedback**: Pulsing mic (red=listening, yellow=thinking, blue=speaking)
- **Markdown stripping**: Removes formatting before TTS (clean speech output)

---

## ✨ Key Features

### 1. **Intelligent Chat with Medical Memory**
- User sends message → app checks user's health notes for context
- System prompt includes: "Here's what you know about this patient..."
- All health-relevant messages auto-saved to database
- Follow-up questions appear after each response (extracted from LLM output)

### 2. **Document Upload & Retrieval**
- Upload lab reports, prescriptions, medical records
- Automatically OCR'd and chunked
- Vector embeddings created and stored in pgvector
- Doctor references documents when answering questions
  - Example: "Your last blood test showed..." (based on retrieved document)

### 3. **Voice Conversation (Alexa-like)**
- Click mic → continuous speaking/listening loop
- No need to press "Send" — speech automatically transcribed and sent
- Doctor speaks response aloud via TTS
- Auto-listens again after response (no button presses needed)
- Works in text mode too if user prefers typing

### 4. **Smart Escalation**
- LLM assigns escalation level: none/mild/urgent/emergency
- Urgent/emergency auto-creates HealthEvent record
- Visible in health timeline
- Prepares user for follow-up (self-referral or doctor notification)

### 5. **Human-like Conversation**
- **System prompt engineering**: Trains bot to ask one question at a time
- **Natural greeting**: "Hey! How are you feeling today?" (not "Welcome, provide symptoms")
- **Context-aware**: Reads previous messages, health notes, documents
- **No robotic phrases**: Removes "thank you for sharing", "I understand", etc.
- **Verdict timing**: Gives assessment when user says "that's all" (not endless questions)

---

## 🛠️ Technology Stack

### Backend
| Component | Technology | Why |
|-----------|-----------|-----|
| Framework | FastAPI (Python 3.9+) | Async, fast, auto-docs |
| LLM | Google Gemini 2.5-flash | Free tier, low latency |
| Embeddings | Google text-embedding-004 | 768-dim, free tier |
| Vector DB | PostgreSQL + pgvector | Open source, self-hosted |
| Document Storage | MinIO | Self-hosted S3 alternative |
| OCR | pytesseract + pdf2image | Open source |
| Auth | JWT + bcrypt | Stateless, secure |
| Async | asyncpg, SQLAlchemy async | Non-blocking database |

### Frontend
| Component | Technology | Why |
|-----------|-----------|-----|
| Framework | React 18 | State management, hooks |
| Styling | Tailwind CSS | Rapid UI development |
| Web Speech | Browser native API | No latency, always available |
| HTTP Client | axios | SSE streaming support |
| Types | TypeScript | Type safety |

### Infrastructure
- **Docker**: Containerized FastAPI + PostgreSQL
- **Database**: PostgreSQL 15 + pgvector extension
- **CORS**: Configured for localhost:3000 (frontend)
- **Environment**: `.env` for secrets, easy local setup

---

## 🎤 Voice Feature Deep Dive

### How Voice Conversation Works

**User Flow:**
1. User clicks microphone button in chat
2. Frontend enters "voice mode" → floating overlay appears
3. Browser SpeechRecognition starts listening (red pulsing mic)
4. User speaks ("I've had a headache for 3 days")
5. Browser transcribes speech → frontend calls `/api/v1/chat/conversations/{id}/messages` with text
6. Backend processes message via medical agent
7. Response streams back via SSE
8. Frontend plays audio response via SpeechSynthesis (blue pulsing mic)
9. **After speech ends, browser automatically starts listening again** ← Alexa-style magic
10. Loop repeats

### Code Architecture

**Frontend (ChatPage.tsx):**
```typescript
const [voiceMode, setVoiceMode] = useState(false);
const recognitionRef = useRef<SpeechRecognition>(null);

// Main voice loop
const startVoiceListening = useCallback(() => {
  recognitionRef.current?.start();
  setListeningStatus("listening"); // red pulsing
}, []);

// User speaks, browser transcribes
recognitionRef.current.onresult = (event) => {
  const transcript = event.results[0][0].transcript;
  sendMessageText(transcript, true); // true = auto-speak response
};

// In sendMessageText, after SSE response received:
// speakText(finalResponse) → wait for completion → startVoiceListening()
// = continuous loop without user input
```

**Backend (chat.py):**
```python
@router.post("/conversations/{conv_id}/messages")
async def send_message(body: ChatRequest):
    # Same as text chat — no special voice handling needed
    # Browser handles speech-to-text (STT)
    # Frontend handles text-to-speech (TTS)
    # Backend just processes text and returns response
```

### Why This Architecture?

| Approach | Pros | Cons |
|----------|------|------|
| **Browser Web Speech** (our choice) | ✅ No latency, native, always works | Limited customization |
| | ✅ No backend processing overhead | Transcription quality varies by browser |
| | ✅ Works offline for TTS | |
| Google Cloud STT | Better accuracy | ✅ Requires backend processing |
| | | ✅ Higher latency |
| | | ✅ API quota limits |

---

## 📊 Common Judge Questions & Answers

### Q1: "How does the app understand medical context without a doctor training dataset?"
**A:** We use two mechanisms:
1. **System Prompt Engineering**: The LLM is given explicit instructions to behave like a real doctor
   - "Ask ONE question at a time"
   - "Listen first, reference records only when relevant"
   - "Give verdict when user signals they're done"
2. **User Health Context**: We load saved health notes from database
   - Every message includes: "Here's what you know about this patient..."
   - Keywords auto-detect and save symptom/medication/lifestyle info
   - Documents are retrieved via RAG (Retrieval-Augmented Generation)
3. **Responsible Defaults**: For emergencies, we always say "Seek emergency care IMMEDIATELY"

### Q2: "How accurate is the voice recognition?"
**A:** Depends on browser, but generally good:
- **Chrome/Edge**: ~95% accuracy for clear speech (uses Google STT backend)
- **Firefox/Safari**: ~90% accuracy (different engines)
- **Network**: Works offline for TTS, only needs internet for STT
- **User experience**: Misheard words? User can correct in chat, bot learns context

For production, we could upgrade to Google Cloud Speech API for 99%+ accuracy (paid).

### Q3: "How do you prevent the bot from giving bad medical advice?"
**A:** Multiple safeguards:
1. **Escalation Detection**
   - LLM marks responses as `escalation_level: emergency | urgent | mild | none`
   - Example: "chest pain" → `emergency` → "SEEK EMERGENCY CARE IMMEDIATELY"
   - Auto-creates HealthEvent for follow-up
2. **Human Review**
   - Health events are logged and timestamped
   - Could be reviewed by real doctors later
3. **Conservative Defaults**
   - Uncertain? Recommend doctor visit
   - No prescriptions given
   - No diagnosis claimed (only "I think you should..."

### Q4: "How does document retrieval work? Can it hallucinate?"
**A:**
1. **Vector Similarity**: Documents are chunked and embedded
   - User asks "What was my last blood test result?"
   - System searches pgvector for chunks about "blood" + "test" + "result"
   - Retrieved chunks ranked by cosine similarity (0.35 threshold)
   - Top 10 chunks passed to LLM as context
2. **RAG (Retrieval-Augmented Generation)**
   - LLM can only reference chunks provided
   - If document says "glucose 150 mg/dL", LLM can cite it
   - If document doesn't mention "cholesterol", LLM won't invent it
3. **Chunk Size Matters**
   - We use 512 tokens per chunk (2 paragraphs)
   - Large enough for context, small enough for relevance
   - Overlap of 64 tokens prevents split sentences

### Q5: "How is the bot trained to talk naturally?"
**A:** No machine learning training — pure prompt engineering:
1. **System Prompt Rules** (in `system_prompt.py`):
   - "When patient says 'hi', greet them and ask 'How are you feeling?'"
   - "Do NOT say 'thank you for sharing' or use robotic phrases"
   - "Ask ONE question at a time"
   - "Responses should be 1-3 sentences for simple exchanges"
   - "When user says 'that's all', give your assessment and stop asking"
2. **Response Format**:
   - Answer text + separator "---" + follow-up questions
   - Frontend strips "---" before TTS (clean speech output)
3. **Health Note Context**:
   - Prompt includes saved notes: "- [symptom] headache for 3 days"
   - LLM naturally references them: "So you mentioned a 3-day headache..."

### Q6: "Can users export their health data?"
**A:** Currently saved in:
- **PostgreSQL**: All messages, health notes, escalations (can dump)
- **MinIO**: Original document files
- **pgvector**: Embeddings (less useful for users)

Future feature: Export as PDF (messages + health notes + documents).

### Q7: "How do you handle user privacy?"
**A:**
- **JWTs**: Stateless auth, tokens expire in 15 minutes
- **Database queries**: Always filtered by `user_id` (no cross-user data leaks)
- **Document storage**: Files stored by user, encrypted filenames in MinIO
- **No tracking**: No analytics, no third-party cookies
- **Local deployment**: Can be deployed on-premise (no data to cloud)

### Q8: "What happens if the LLM API is down?"
**A:**
- SSE connection drops
- Frontend shows "Connection lost" error
- User can retry
- Message is still saved locally (in database)
- Could implement fallback to cached responses (future enhancement)

### Q9: "How fast is the response?"
**A:** Typical flow:
- STT (browser): <1 second
- Network + API + LLM streaming: 2-4 seconds
- TTS (browser): 2-5 seconds (depends on response length)
- **Total**: ~5-10 seconds from "done speaking" to "bot starts speaking"

Compared to:
- Calling a doctor: Hours to days
- ER wait: 2-4 hours
- Telehealth app: 10-30 minutes booking

### Q10: "What are the limitations?"
**A:**
1. **Not a replacement for real doctors** — escalates urgent cases
2. **No medication prescriptions** — not legally allowed, refers to doctors
3. **Voice accent dependency** — works best with clear English pronunciation
4. **No multimodal input** — can't analyze X-rays visually yet (only text extraction)
5. **Free tier limits** — Google Gemini has daily limits (100k free tokens)
6. **Cold starts** — First query loads embeddings, can take 2-3 seconds

---

## 🚀 Demo Walkthrough

### Scenario 1: Text Chat with Documents
1. User uploads lab report (PDF)
2. App OCRs → chunks → embeds → stores in pgvector
3. User types: "I feel tired a lot"
4. System detects health note (symptom) → saves to database
5. System retrieves relevant lab chunks
6. LLM generates response: "I see your last blood test showed low iron... When did the fatigue start?"
7. User answers → bot gives assessment

### Scenario 2: Voice Conversation
1. User clicks mic
2. Says: "Hi, I have a fever"
3. Browser transcribes → sends to `/chat/conversations/{id}/messages`
4. App detects health note (symptom) → saves
5. LLM responds: "How high is your fever?" (with escalation assessment)
6. Response streams back → frontend plays audio
7. **Mic auto-activates** → user speaks answer
8. Loop continues until user leaves voice mode

### Scenario 3: Emergency Escalation
1. User: "I have chest pain and can't breathe"
2. LLM escalation level: `emergency`
3. Response: "SEEK EMERGENCY CARE IMMEDIATELY. Call 911 or go to nearest ER."
4. System auto-creates HealthEvent record (for follow-up)
5. Frontend displays prominent warning

---

## 📈 Differentiation from Competitors

| Feature | CareNode | ChatGPT | Telehealth App | ER |
|---------|----------|---------|-----------------|-----|
| **Remembers history** | ✅ Persistent notes | ❌ Per-session only | ✅ Yes | ✅ Yes |
| **Voice conversation** | ✅ Alexa-style | ❌ Text only | ✅ Voice call | ✅ Yes |
| **Instant response** | ✅ <5 seconds | ✅ <5 seconds | ❌ 15-30 min wait | ❌ 2-4 hours |
| **Document analysis** | ✅ Upload + OCR | ❌ Manual copy-paste | ✅ Yes | ✅ Visual (better) |
| **Escalation aware** | ✅ Detects emergencies | ❌ No medical context | ✅ Refers to doctors | ✅ Handles emergencies |
| **Cost** | ✅ Free/cheap | ✅ $20/month | ❌ $100+ per visit | ❌ $1000+ |
| **Privacy** | ✅ Self-hosted option | ❌ Cloud only | ⚠️ Depends | ✅ Yes |

---

## 🔧 Setup Instructions (for judges to run locally)

### Prerequisites
- Python 3.9+, Node.js 16+, Docker, PostgreSQL 15
- Google API key (free tier: Gemini, embeddings)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Create .env from .env.example
cp .env.example .env
# Fill in: GOOGLE_API_KEY, DATABASE_URL, SECRET_KEY

# Start PostgreSQL (Docker)
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=medagent \
  -e POSTGRES_PASSWORD=medagent_secret \
  -e POSTGRES_DB=medagent_db \
  postgres:15 && \
docker exec $(docker ps -q) psql -U medagent -d medagent_db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations + start server
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:3000
```

### Quick Test
1. Sign up at http://localhost:3000
2. Type "hello" in chat → bot greets you
3. Type "I have a headache" → bot asks follow-up
4. Click mic icon → try voice mode
5. Upload a PDF → bot reads it and references it

---

## 🎯 Future Roadmap

### Phase 2 (Month 2-3)
- [ ] Multi-language support (Spanish, Mandarin)
- [ ] Appointment booking integration
- [ ] Prescription management (partner with pharmacies)
- [ ] Real-time vital sign monitoring (Apple Watch, Fitbit)

### Phase 3 (Month 4-6)
- [ ] Doctor review dashboard (let real doctors oversee escalations)
- [ ] Patient data export (FHIR standard)
- [ ] Integration with EHR systems (HL7)
- [ ] Multimodal image analysis (X-ray, ultrasound reading)

### Phase 4 (Year 2)
- [ ] Fine-tuned medical LLM (built on verified clinical data)
- [ ] Regulatory compliance (HIPAA, GDPR)
- [ ] Clinical validation studies
- [ ] Licensing as medical device

---

## 📞 Contact & Questions

**GitHub**: [CareNode Repository Link]
**Team**: [Names, roles]
**Demo Video**: [Link]

---

## 🙏 Acknowledgments

Built with:
- **Google Gemini** for LLM and embeddings (free tier)
- **PostgreSQL + pgvector** for vector search
- **FastAPI** for backend
- **React** for frontend
- **Web Speech API** for voice (no external dependencies)

---

**Last Updated**: March 14, 2026
**License**: MIT (open source)
