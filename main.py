from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import asyncio
import base64
import os
import uuid
from io import BytesIO

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

TTS_DIRECTORY = "tts"
os.makedirs(TTS_DIRECTORY, exist_ok=True)

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
        "pipeline": "Audio -> STT -> LLM/RAG -> TTS -> Audio",
    }


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Voice AI Demo UI</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 2rem; background: #f2f6fb; color: #111; }
        .container { max-width: 720px; margin: 0 auto; padding: 1.5rem; background: #fff; border-radius: 12px; box-shadow: 0 10px 24px rgba(0,0,0,0.08); }
        h1 { margin-top: 0; }
        .row { margin-top: 1rem; }
        textarea { width: 100%; padding: 0.85rem; font-size: 1rem; border-radius: 8px; border: 1px solid #ccd6eb; resize: vertical; }
        button { margin-top: 0.75rem; padding: 0.85rem 1.2rem; border: none; border-radius: 8px; background: #2563eb; color: white; cursor: pointer; font-size: 1rem; }
        button:hover { background: #1e4db7; }
        button:disabled { background: #94a3b8; cursor: not-allowed; }
        .output { margin-top: 1.5rem; }
        .output p { margin: 0.5rem 0; }
        .output audio { margin-top: 1rem; width: 100%; }
        .status, .error { margin-top: 1rem; }
        .error { color: #b91c1c; }
        .controls { display: flex; gap: 1rem; flex-wrap: wrap; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Voice AI Demo UI</h1>
        <p>Record audio in your browser and upload it to the server for STT, LLM response generation, and TTS playback.</p>

        <div class="controls">
          <button id="record-btn" type="button">Start recording</button>
          <button id="send-audio-btn" type="button" disabled>Send audio</button>
          <button id="send-text-btn" type="button">Send manual text</button>
        </div>

        <div class="status" id="status">Press "Start recording" to capture audio.</div>

        <div class="output" id="recorded-block" hidden>
          <p><strong>Recorded audio ready.</strong></p>
          <p id="recorded-info"></p>
        </div>

        <div class="row">
          <label for="audio_text"><strong>Manual fallback text</strong> (optional)</label>
          <textarea id="audio_text" rows="4">I want to book an appointment</textarea>
        </div>

        <div class="output" id="result" hidden>
          <p><strong>Transcript:</strong> <span id="result-transcript"></span></p>
          <p><strong>LLM response:</strong> <span id="reply"></span></p>
          <div id="audio-player"></div>
        </div>
        <div class="error" id="error" hidden></div>
      </div>

      <script>
        const recordBtn = document.getElementById('record-btn');
        const sendAudioBtn = document.getElementById('send-audio-btn');
        const sendTextBtn = document.getElementById('send-text-btn');
        const statusEl = document.getElementById('status');
        const recordedBlock = document.getElementById('recorded-block');
        const recordedInfo = document.getElementById('recorded-info');
        const resultEl = document.getElementById('result');
        const resultTranscriptEl = document.getElementById('result-transcript');
        const replyEl = document.getElementById('reply');
        const audioPlayerEl = document.getElementById('audio-player');
        const errorEl = document.getElementById('error');
        const textArea = document.getElementById('audio_text');

        let audioContext;
        let mediaStream;
        let sourceNode;
        let processorNode;
        let recordedBuffers = [];
        let recording = false;
        let audioBlob = null;
        let sampleRate = 44100;

        function writeString(view, offset, string) {
          for (let i = 0; i < string.length; i += 1) {
            view.setUint8(offset + i, string.charCodeAt(i));
          }
        }

        function floatTo16BitPCM(output, offset, input) {
          for (let i = 0; i < input.length; i += 1, offset += 2) {
            let s = Math.max(-1, Math.min(1, input[i]));
            output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
          }
        }

        function encodeWAV(samples, sampleRate) {
          const buffer = new ArrayBuffer(44 + samples.length * 2);
          const view = new DataView(buffer);

          writeString(view, 0, 'RIFF');
          view.setUint32(4, 36 + samples.length * 2, true);
          writeString(view, 8, 'WAVE');
          writeString(view, 12, 'fmt ');
          view.setUint32(16, 16, true);
          view.setUint16(20, 1, true);
          view.setUint16(22, 1, true);
          view.setUint32(24, sampleRate, true);
          view.setUint32(28, sampleRate * 2, true);
          view.setUint16(32, 2, true);
          view.setUint16(34, 16, true);
          writeString(view, 36, 'data');
          view.setUint32(40, samples.length * 2, true);
          floatTo16BitPCM(view, 44, samples);
          return new Blob([view], { type: 'audio/wav' });
        }

        function mergeBuffers(buffers, length) {
          const result = new Float32Array(length);
          let offset = 0;
          for (const buffer of buffers) {
            result.set(buffer, offset);
            offset += buffer.length;
          }
          return result;
        }

        function resetRecording() {
          recordedBuffers = [];
          audioBlob = null;
          recordedBlock.hidden = true;
          sendAudioBtn.disabled = true;
          resultEl.hidden = true;
          errorEl.hidden = true;
        }

        async function startRecording() {
          resetRecording();
          mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          audioContext = new (window.AudioContext || window.webkitAudioContext)();
          sampleRate = audioContext.sampleRate;
          sourceNode = audioContext.createMediaStreamSource(mediaStream);
          processorNode = audioContext.createScriptProcessor(4096, 1, 1);

          processorNode.onaudioprocess = (event) => {
            if (!recording) return;
            recordedBuffers.push(new Float32Array(event.inputBuffer.getChannelData(0)));
          };

          sourceNode.connect(processorNode);
          processorNode.connect(audioContext.destination);
          recording = true;
          recordBtn.textContent = 'Stop recording';
          sendAudioBtn.disabled = true;
          recordedBlock.hidden = true;
          resultEl.hidden = true;
          errorEl.hidden = true;
          statusEl.textContent = 'Recording...';
        }

        function stopRecording() {
          recording = false;
          recordBtn.textContent = 'Start recording';
          processorNode.disconnect();
          sourceNode.disconnect();
          mediaStream.getTracks().forEach((track) => track.stop());
          audioContext.close();

          const length = recordedBuffers.reduce((sum, buffer) => sum + buffer.length, 0);
          const merged = mergeBuffers(recordedBuffers, length);
          audioBlob = encodeWAV(merged, sampleRate);
          recordedBlock.hidden = false;
          recordedInfo.textContent = `Captured audio (${Math.round(audioBlob.size / 1024)} KB)`;
          sendAudioBtn.disabled = false;
          statusEl.textContent = 'Audio captured. Click Send audio to process it.';
        }

        recordBtn.addEventListener('click', async () => {
          if (recording) {
            stopRecording();
            return;
          }

          try {
            await startRecording();
          } catch (error) {
            errorEl.textContent = 'Microphone access failed: ' + error.message;
            errorEl.hidden = false;
          }
        });

        async function handleResponse(response) {
          if (!response.ok) {
            const err = await response.json().catch(() => null);
            throw new Error(err?.detail || `Server returned ${response.status}`);
          }
          return response.json();
        }

        async function processResult(data) {
          resultTranscriptEl.textContent = data.stt_transcript;
          replyEl.textContent = data.llm_response;
          resultEl.hidden = false;
          audioPlayerEl.innerHTML = '';
          if (data.tts_output_url) {
            const audio = document.createElement('audio');
            audio.controls = true;
            audio.src = data.tts_output_url;
            audioPlayerEl.appendChild(audio);
          }
        }

        sendAudioBtn.addEventListener('click', async () => {
          if (!audioBlob) {
            errorEl.textContent = 'No recorded audio available.';
            errorEl.hidden = false;
            return;
          }
          errorEl.hidden = true;
          resultEl.hidden = true;
          audioPlayerEl.innerHTML = '';

          const formData = new FormData();
          formData.append('file', audioBlob, 'recording.wav');

          try {
            const response = await fetch('/voice-agent/audio', {
              method: 'POST',
              body: formData,
            });
            const data = await handleResponse(response);
            await processResult(data);
          } catch (error) {
            errorEl.textContent = error.message;
            errorEl.hidden = false;
          }
        });

        sendTextBtn.addEventListener('click', async () => {
          errorEl.hidden = true;
          resultEl.hidden = true;
          audioPlayerEl.innerHTML = '';

          const audioText = textArea.value.trim();
          if (!audioText) {
            errorEl.textContent = 'Please enter some text to send.';
            errorEl.hidden = false;
            return;
          }

          try {
            const response = await fetch('/voice-agent/mock', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ audio_text: audioText }),
            });
            const data = await handleResponse(response);
            await processResult(data);
          } catch (error) {
            errorEl.textContent = error.message;
            errorEl.hidden = false;
          }
        });
      </script>
    </body>
    </html>
    """


@app.post("/chat")
def chat(request: ChatRequest):
    """Normal REST API endpoint for text chat."""
    reply = simple_llm_response(request.message)
    return {"input": request.message, "reply": reply}


@app.post("/voice-agent/mock")
def voice_agent_mock(request: VoiceMockRequest):
    """Mock voice-agent pipeline: STT -> LLM/RAG -> TTS."""
    transcript = request.audio_text
    reply_text = simple_llm_response(transcript)

    tts_filename = f"tts_response_{uuid.uuid4().hex}.mp3"
    tts_path = os.path.join(TTS_DIRECTORY, tts_filename)
    tts = gTTS(text=reply_text, lang="en")
    tts.save(tts_path)

    with open(tts_path, "rb") as audio_file:
        audio_bytes = audio_file.read()

    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    audio_html = f'<audio controls src="/tts/{tts_filename}"></audio>'

    return {
        "stt_transcript": transcript,
        "llm_response": reply_text,
        "tts_output_url": f"/tts/{tts_filename}",
        "tts_output_base64": audio_base64,
        "tts_output_html": audio_html,
    }


def recognize_speech_from_wav(wav_bytes: bytes) -> str:
    if sr is None:
        raise HTTPException(status_code=500, detail="SpeechRecognition library is not installed.")

    recognizer = sr.Recognizer()
    with sr.AudioFile(BytesIO(wav_bytes)) as source:
        audio_data = recognizer.record(source)

    try:
        return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        raise HTTPException(status_code=500, detail=f"STT provider error: {e}")


@app.post("/voice-agent/audio")
async def voice_agent_audio(file: UploadFile = File(...)):
    """Real audio pipeline: upload WAV file, run STT, LLM, and TTS."""
    if file.content_type not in ("audio/wav", "audio/x-wav", "audio/wave"):
        raise HTTPException(status_code=400, detail="Only WAV audio uploads are supported.")

    audio_bytes = await file.read()
    transcript = recognize_speech_from_wav(audio_bytes)
    if not transcript:
        raise HTTPException(status_code=400, detail="Could not transcribe the uploaded audio.")

    reply_text = simple_llm_response(transcript)

    tts_filename = f"tts_response_{uuid.uuid4().hex}.mp3"
    tts_path = os.path.join(TTS_DIRECTORY, tts_filename)
    tts = gTTS(text=reply_text, lang="en")
    tts.save(tts_path)

    with open(tts_path, "rb") as audio_file:
        audio_bytes = audio_file.read()

    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    audio_html = f'<audio controls src="/tts/{tts_filename}"></audio>'

    return {
        "stt_transcript": transcript,
        "llm_response": reply_text,
        "tts_output_url": f"/tts/{tts_filename}",
        "tts_output_base64": audio_base64,
        "tts_output_html": audio_html,
    }


@app.get("/tts/{filename}")
def get_tts_audio(filename: str):
    file_path = os.path.abspath(os.path.join(TTS_DIRECTORY, filename))
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Audio file not found")


@app.websocket("/ws/voice")
async def websocket_voice_demo(websocket: WebSocket):
    """WebSocket demo for live text transcript simulation."""
    await websocket.accept()
    await websocket.send_json(
        {"message": "WebSocket connected. Send text chunks to simulate live voice."}
    )

    while True:
        chunk = await websocket.receive_text()
        await websocket.send_json({"partial_transcript": chunk})

        if chunk.lower().strip() in ["bye", "exit", "stop"]:
            await websocket.send_json({"reply": "Session ended."})
            break

        await asyncio.sleep(0.2)
        await websocket.send_json({"reply": simple_llm_response(chunk)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
