# Voice AI FastAPI Demo

A beginner-friendly backend demo for an AI Voice Engineer role.

## What this project shows
This project demonstrates the basic backend structure of a voice AI agent:

**Audio Input → STT → LLM/RAG → TTS → Audio Output**

This is a mock implementation. It does not use real paid APIs, but the structure is similar to a production voice AI backend.

## Features
- FastAPI backend
- REST endpoint for chat
- Mock voice-agent pipeline
- WebSocket endpoint for real-time communication demo
- Clean project structure for future STT/TTS/LLM integration

## Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Example REST Request

Endpoint:

```text
POST /voice-agent/mock
```

Body:

```json
{
  "audio_text": "I want to book an appointment"
}
```

## Interview Explanation
I built this mini project to show my understanding of how a voice AI backend works. In a real system, the audio would be sent to an STT provider like Whisper or Deepgram, the transcript would be processed by an LLM or RAG pipeline, and the final text response would be converted into speech using a TTS service like ElevenLabs or Azure TTS.
