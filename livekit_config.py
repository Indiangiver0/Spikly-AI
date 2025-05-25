# LiveKit Configuration
import os

# LiveKit Server Configuration
LIVEKIT_URL = "wss://spikly-ai-2p27m8so.livekit.cloud"
LIVEKIT_API_KEY = "APIHxKr3wPe6No5"
LIVEKIT_API_SECRET = "l7ZMQFSV2NUHVqFpwJUTb5uncw6T5e4rcdsO1jUQXEc"

# Set environment variables for LiveKit
os.environ["LIVEKIT_URL"] = LIVEKIT_URL
os.environ["LIVEKIT_API_KEY"] = LIVEKIT_API_KEY
os.environ["LIVEKIT_API_SECRET"] = LIVEKIT_API_SECRET

# Voice settings
VOICE_SETTINGS = {
    "sample_rate": 16000,
    "channels": 1,
    "chunk_duration": 0.1,  # 100ms chunks
    "silence_threshold": 0.01,
    "silence_duration": 1.0,  # 1 second of silence to stop recording
}

# TTS Settings
TTS_SETTINGS = {
    "voice": "alloy",  # OpenAI TTS voice
    "model": "tts-1",
    "speed": 1.0
}

# STT Settings  
STT_SETTINGS = {
    "model": "whisper-1",
    "language": "en",
    "temperature": 0.0
} 