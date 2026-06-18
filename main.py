from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
import time

app = FastAPI(title="Voice AI FastAPI Demo")


class ChatRequest(BaseModel):
    message: str


class VoiceMockRequest(BaseModel):
    audio_text: str


def simple_llm_response(user_text: str) -> str:
    """Mock LLM response. Replace this with a real LLM API later."""
    text = user_text.lower()

    if "appointment" in text:
        return "Sure, I can help you book an appointment. Please share your preferred date and time."
    if "rag" in text:
        return "RAG means Retrieval-Augmented Generation. It helps AI answer using relevant documents."
    if "voice ai" in text:
        return "A voice AI system uses STT, an LLM or RAG pipeline, and TTS to respond by voice."

    return f"I understood your message: '{user_text}'. How can I help further?"


@app.get("/")
def home():
    return {
        "status": "running",
        "project": "Voice AI FastAPI Demo",
        "pipeline": "Audio -> STT -> LLM/RAG -> TTS -> Audio"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    """Normal REST API endpoint for text chat."""
    reply = simple_llm_response(request.message)
    return {
        "input": request.message,
        "reply": reply
    }


@app.post("/voice-agent/mock")
def voice_agent_mock(request: VoiceMockRequest):
    """
    Mock voice-agent pipeline.
    In a real system:
    1. audio file/stream goes to STT
    2. transcript goes to LLM/RAG
    3. reply goes to TTS
    """

    # Mock STT: assume audio_text is already the transcript
    transcript = request.audio_text

    # Mock LLM
    reply_text = simple_llm_response(transcript)

    # Mock TTS output
    audio_response = "tts_audio_url_or_stream_would_be_returned_here"

    return {
        "stt_transcript": transcript,
        "llm_response": reply_text,
        "tts_output": audio_response
    }


@app.websocket("/ws/voice")
async def websocket_voice_demo(websocket: WebSocket):
    """
    Simple WebSocket demo.
    Send text chunks and receive live mock AI replies.
    This represents how real-time audio chunks could be streamed.
    """
    await websocket.accept()
    await websocket.send_json({"message": "WebSocket connected. Send text chunks to simulate live voice."})

    while True:
        chunk = await websocket.receive_text()
        await websocket.send_json({"partial_transcript": chunk})

        if chunk.lower().strip() in ["bye", "exit", "stop"]:
            await websocket.send_json({"reply": "Session ended."})
            break

        time.sleep(0.2)
        await websocket.send_json({"reply": simple_llm_response(chunk)})
