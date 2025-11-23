# Chat API Gateway

🚀 **[Live Demo](https://chat-api-gateway-production.up.railway.app/docs)** | 📦 **[GitHub](https://github.com/Punsach/chat-api-gateway)**

Production-grade API gateway with authentication, rate limiting, and streaming chat completions.

**Try it live:** https://chat-api-gateway-production.up.railway.app

## ✨ Quick Start (Live API)
```bash
# 1. Create an account
curl -X POST https://chat-api-gateway-production.up.railway.app/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'

# 2. Login and get token
curl -X POST https://chat-api-gateway-production.up.railway.app/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'

# 3. Try the chat API
curl -X POST https://chat-api-gateway-production.up.railway.app/v1/chat/completions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}], "stream": false}'
```

Or explore the interactive docs: **[/docs](https://chat-api-gateway-production.up.railway.app/docs)**

---


## 🚀 Features

- **Multi-method Authentication**: JWT tokens (short-lived) + API keys (long-lived)
- **Tiered Rate Limiting**: Token bucket algorithm with Redis (10 req/min free, 100 req/min pro)
- **Streaming Responses**: Server-Sent Events (SSE) for real-time token streaming
- **OpenAI-Compatible API**: Drop-in compatible with OpenAI's chat completions format
- **Production Observability**: Rate limit headers, graceful degradation, fail-open design

## 🏗️ Architecture
```
┌─────────────────────────────────────────────────────────┐
│                     Client Request                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               FastAPI Gateway (main.py)                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │  1. Auth Middleware (auth.py)                    │   │
│  │     - Validate JWT or API key                    │   │
│  │     - Extract user & tier                        │   │
│  └─────────────────┬────────────────────────────────┘   │
│                    │                                    │
│  ┌─────────────────▼────────────────────────────────┐   │
│  │  2. Rate Limiter (rate_limiter.py)               │   │
│  │     - Token bucket per user                      │   │
│  │     - Redis-backed (distributed)                 │   │
│  │     - Fail open on Redis errors                  │   │
│  └─────────────────┬────────────────────────────────┘   │
│                    │                                    │
│  ┌─────────────────▼────────────────────────────────┐   │
│  │  3. Chat Completions Endpoint                    │   │
│  │     - Stream via SSE or full response            │   │
│  │     - Mock LLM backend (llm.py)                  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
┌──────────────────┐        ┌──────────────────┐
│  PostgreSQL      │        │  Redis           │
│  - Users         │        │  - Rate limits   │
│  - API keys      │        │  - Token buckets │
└──────────────────┘        └──────────────────┘
```

## 🛠️ Tech Stack

- **FastAPI**: Modern Python web framework with async support
- **PostgreSQL**: User & API key storage
- **Redis**: Distributed rate limiting
- **SQLAlchemy**: ORM for database operations
- **Pydantic**: Request/response validation
- **python-jose**: JWT token creation/validation
- **bcrypt**: Password hashing

## 📦 Installation

### Prerequisites
- Python 3.11+
- Docker & Docker Compose

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/chat-api-gateway.git
cd chat-api-gateway
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start database services**
```bash
docker-compose up -d
```

5. **Create test user**
```bash
python << 'EOF'
from app.database import SessionLocal, User
import bcrypt

db = SessionLocal()
user = User(
    email="test@example.com",
    hashed_password=bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
    tier="free"
)
db.add(user)
db.commit()
print(f"✅ Test user created: {user.email}")
db.close()
EOF
```

6. **Run the server**
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## 🧪 Usage Examples

### 1. Login & Get JWT
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Create API Key
```bash
curl -X POST http://localhost:8000/v1/auth/api-keys \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Key"}'
```

Response:
```json
{
  "api_key": "sk-5xP2jKl9mN4qR8tY1wZ3vC6bH8nL0pM4...",
  "name": "My API Key"
}
```

### 3. Chat Completion (Non-Streaming)
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Tell me a joke"}],
    "model": "gpt-3.5-turbo",
    "stream": false
  }'
```

### 4. Chat Completion (Streaming)
```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Write Python code"}],
    "model": "gpt-3.5-turbo",
    "stream": true
  }'
```

## 🔐 API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | No | Health check |
| `/v1/auth/login` | POST | No | Email/password → JWT |
| `/v1/auth/api-keys` | POST | Yes | Create API key |
| `/v1/auth/me` | GET | Yes | Get current user info |
| `/v1/chat/completions` | POST | Yes | OpenAI-compatible chat |

## ⚡ Rate Limits

| Tier | Requests/Minute |
|------|-----------------|
| Free | 10 |
| Pro | 100 |
| Enterprise | 1,000 |
| Global (all users) | 10,000 |

Headers returned:
- `X-RateLimit-Limit`: Max requests per minute
- `X-RateLimit-Remaining`: Requests remaining
- `Retry-After`: Seconds to wait (on 429 errors)

## 🎯 Design Decisions

### Why Token Bucket Algorithm?
- **Smooth rate limiting**: Tokens refill continuously (not reset every minute)
- **Allows bursts**: Users can save tokens for occasional spikes
- **Efficient**: Only stores 2 values per user in Redis
- **Fair**: No boundary gaming (vs fixed window)

### Why Both JWT and API Keys?
- **JWT**: Short-lived (30 min), stateless, ideal for web/mobile apps
- **API Keys**: Long-lived, revocable, ideal for server-to-server integrations
- **Trade-off**: JWTs can't be revoked before expiration (mitigated by short TTL)

### Why Fail Open on Redis Errors?
- **Availability > Perfect Rate Limiting**: API stays up even if Redis crashes
- **User Experience**: Better to occasionally exceed limits than take down service
- **Monitoring**: Alerts fire if Redis is down, but users unaffected

### Why Server-Sent Events (SSE) for Streaming?
- **Simpler than WebSockets**: Unidirectional (server → client)
- **HTTP-compatible**: Works through proxies/firewalls
- **Automatic reconnection**: Browsers handle it natively
- **OpenAI standard**: Industry convention for LLM streaming

## 📊 Performance Characteristics

- **Auth latency**: ~5ms (JWT decode) or ~10ms (API key DB lookup)
- **Rate limit check**: ~2ms (Redis roundtrip)
- **Streaming first token**: ~50ms (simulated LLM latency)
- **Max throughput**: 10k req/min (global limit, tunable)

## 🧪 Testing

Run the test suite:
```bash
# Test authentication
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Test rate limiting (should see 429 after 10 requests)
for i in {1..12}; do
  curl -i http://localhost:8000/v1/auth/me \
    -H "Authorization: Bearer YOUR_TOKEN" 2>/dev/null | grep "HTTP"
done
```

## 🚀 Deployment

### Railway
```bash
# Install Railway CLI
npm install -g railway

# Login and deploy
railway login
railway init
railway up
```

Add these environment variables in Railway dashboard:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Random 32-character string

### Fly.io
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy
fly launch
fly secrets set SECRET_KEY=your-secret-key
```

## 🔮 Future Enhancements

- [ ] Prometheus metrics endpoint (`/metrics`)
- [ ] Idempotency keys for POST requests
- [ ] OpenTelemetry distributed tracing
- [ ] Webhook delivery system
- [ ] Multi-region deployment
- [ ] Refresh token rotation
- [ ] RBAC (role-based access control)

## 📖 Project Structure
```
chat-api-gateway/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + endpoints
│   ├── auth.py              # JWT + API key validation
│   ├── rate_limiter.py      # Token bucket algorithm
│   ├── models.py            # Pydantic request/response schemas
│   ├── database.py          # SQLAlchemy models
│   ├── llm.py               # Mock LLM backend
│   ├── metrics.py           # Prometheus metrics (future)
│   └── tracing.py           # OpenTelemetry (future)
├── tests/
│   └── test_api.py
├── docker-compose.yml       # Redis + Postgres
├── requirements.txt
└── README.md
```

## 🎓 Learning Outcomes

This project demonstrates:
- **Authentication patterns**: JWT vs API keys, when to use each
- **Distributed systems**: Rate limiting with Redis, graceful degradation
- **Real-time APIs**: Server-Sent Events for streaming
- **Production patterns**: Fail-open design, observability headers
- **API design**: RESTful conventions, OpenAI compatibility

## 📝 License

MIT

## 👤 Author

Built as a portfolio project for backend engineering interviews.

---

**⭐ If you found this useful, please star the repo!**