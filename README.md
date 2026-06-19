# Voice AI FastAPI Demo

Simple FastAPI demo of a voice AI pipeline.

## What it does
- Accepts text or WAV audio input
- Converts audio to text (STT)
- Generates a response with a mock LLM
- Returns speech output as MP3 (TTS)

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open in your browser:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/ui`

## Test the mock endpoint

POST `/voice-agent/mock`

```json
{ "audio_text": "I want to book an appointment" }
```


## Explanation
I built this mini project to show my understanding of how a voice AI backend works. In a real system, the audio would be sent to an STT provider like Whisper or Deepgram, the transcript would be processed by an LLM or RAG pipeline, and the final text response would be converted into speech using a TTS service like ElevenLabs or Azure TTS.
