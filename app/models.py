# app/models.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class APIKeyCreate(BaseModel):
    name: str

class APIKeyResponse(BaseModel):
    api_key: str
    name: str

class Message(BaseModel):
    role: str  # system, user, assistant
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    stream: bool = False
    max_tokens: Optional[int] = None