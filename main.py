from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Literal
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: Literal['system', 'user', 'assistant']
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]

@app.post("/chat")
def chat_with_model(request: ChatRequest):
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": request.model,
                "messages": [msg.dict() for msg in request.messages],
                "stream": False
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        data = response.json()
        return {"response": data.get("message", {}).get("content", "")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
