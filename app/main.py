# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from app.auth import (
    create_access_token,
    verify_password,
    get_current_user,
    generate_api_key,
    get_db,
    security
)
from app.database import User, APIKey
from app.models import LoginRequest, LoginResponse, APIKeyCreate, APIKeyResponse, ChatRequest, Message
from app.rate_limiter import RateLimiter
from fastapi.security import HTTPAuthorizationCredentials
from app.llm import mock_llm_stream, mock_llm_complete
import json
import uuid
import time as time_module

app = FastAPI(title="Chat API Gateway")

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limit all requests except auth endpoints"""
    
    # Skip rate limiting ONLY for these specific paths
    skip_paths = [
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/v1/auth/login",
        "/v1/auth/api-keys"
    ]
    
    if request.url.path in skip_paths:
        return await call_next(request)
    
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return await call_next(request)
    
    try:
        # Extract token
        token = auth_header.replace("Bearer ", "")
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Validate user
            user = await get_current_user(credentials, db)
            
            # Check rate limit
            limiter = RateLimiter(tier=user.tier, user_id=user.id)
            allowed, info = limiter.check()
            
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": info["error"],
                        "detail": f"Rate limit exceeded. Try again in {info['retry_after']} seconds."
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": str(info["retry_after"])
                    }
                )
            
            # Add rate limit headers to response
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            return response
            
        finally:
            db.close()
            
    except Exception as e:
        # If anything fails, let the request through (fail open)
        return await call_next(request)

@app.get("/")
async def root():
    return {"message": "Chat API Gateway", "status": "running"}

@app.post("/v1/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email/password, get JWT"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.id})
    return LoginResponse(access_token=access_token)

@app.post("/v1/auth/signup")
async def signup(request: LoginRequest, db: Session = Depends(get_db)):
    """Create new user account"""
    import bcrypt
    
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=request.email,
        hashed_password=bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode(),
        tier="free"
    )
    db.add(user)
    db.commit()
    
    return {"message": "User created successfully", "email": user.email}

@app.post("/v1/auth/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new API key for authenticated user"""
    key = generate_api_key()
    api_key = APIKey(
        key=key,
        user_id=current_user.id,
        name=request.name
    )
    db.add(api_key)
    db.commit()
    return APIKeyResponse(api_key=key, name=request.name)

@app.get("/v1/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "tier": current_user.tier
    }

@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    OpenAI-compatible chat completions endpoint
    Supports both streaming and non-streaming responses
    """
    
    # Convert Pydantic messages to dicts
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    # Streaming response
    if request.stream:
        def generate():
            chunk_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
            
            # Stream tokens
            for token in mock_llm_stream(messages, request.model):
                chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time_module.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": token},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            
            # Final chunk
            final_chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time_module.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
    
    # Non-streaming response
    response_text = mock_llm_complete(messages, request.model)
    response = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time_module.time()),
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": sum(len(m["content"].split()) for m in messages),
            "completion_tokens": len(response_text.split()),
            "total_tokens": sum(len(m["content"].split()) for m in messages) + len(response_text.split())
        }
    }
    
    return response