import asyncio
import io
import wave
import pyaudio
import threading
from typing import Optional, Callable
from openai import OpenAI
from config import OPENAI_API_KEY
from livekit_config import VOICE_SETTINGS, TTS_SETTINGS, STT_SETTINGS
import tempfile
import os

class VoiceHandler:
    """Handles voice recording, STT, TTS, and audio playback"""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.is_playing = False
        self.recording_thread = None
        self.audio_data = []
        
        # Audio settings
        self.sample_rate = VOICE_SETTINGS["sample_rate"]
        self.channels = VOICE_SETTINGS["channels"]
        self.chunk_size = int(self.sample_rate * VOICE_SETTINGS["chunk_duration"])
        self.silence_threshold = VOICE_SETTINGS["silence_threshold"]
        self.silence_duration = VOICE_SETTINGS["silence_duration"]
        
        # Callbacks
        self.on_recording_start: Optional[Callable] = None
        self.on_recording_stop: Optional[Callable] = None
        self.on_transcription_ready: Optional[Callable[[str], None]] = None
        self.on_audio_ready: Optional[Callable[[bytes], None]] = None
        
    def start_recording(self):
        """Starts voice recording in a separate thread"""
        if self.is_recording:
            return
            
        self.is_recording = True
        self.audio_data = []
        
        if self.on_recording_start:
            self.on_recording_start()
            
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
    def stop_recording(self):
        """Stops voice recording"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        
        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)
            
        if self.on_recording_stop:
            self.on_recording_stop()
            
    def _record_audio(self):
        """Internal method to record audio"""
        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            silence_counter = 0
            max_silence_chunks = int(self.silence_duration * self.sample_rate / self.chunk_size)
            
            while self.is_recording:
                try:
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    self.audio_data.append(data)
                    
                    # Simple silence detection
                    audio_level = max(data) if data else 0
                    if audio_level < self.silence_threshold * 32767:  # 16-bit audio
                        silence_counter += 1
                        if silence_counter >= max_silence_chunks:
                            break
                    else:
                        silence_counter = 0
                        
                except Exception as e:
                    print(f"Error reading audio: {e}")
                    break
                    
            stream.stop_stream()
            stream.close()
            
            # Auto-stop recording after silence
            if self.is_recording:
                self.stop_recording()
                
        except Exception as e:
            print(f"Error in audio recording: {e}")
            self.is_recording = False
            
    async def transcribe_audio(self) -> Optional[str]:
        """Transcribes recorded audio using OpenAI Whisper"""
        if not self.audio_data:
            return None
            
        try:
            # Convert audio data to WAV format
            audio_bytes = b''.join(self.audio_data)
            
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(self.channels)
                    wav_file.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio_bytes)
                
                # Transcribe using OpenAI
                with open(temp_file.name, 'rb') as audio_file:
                    response = await asyncio.to_thread(
                        self.client.audio.transcriptions.create,
                        model=STT_SETTINGS["model"],
                        file=audio_file,
                        language=STT_SETTINGS["language"],
                        temperature=STT_SETTINGS["temperature"]
                    )
                    
                # Clean up temp file
                os.unlink(temp_file.name)
                
                transcription = response.text.strip()
                
                if self.on_transcription_ready and transcription:
                    self.on_transcription_ready(transcription)
                    
                return transcription
                
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None
            
    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """Converts text to speech using OpenAI TTS"""
        if not text.strip():
            return None
            
        try:
            response = await asyncio.to_thread(
                self.client.audio.speech.create,
                model=TTS_SETTINGS["model"],
                voice=TTS_SETTINGS["voice"],
                input=text,
                speed=TTS_SETTINGS["speed"]
            )
            
            audio_data = response.content
            
            if self.on_audio_ready:
                self.on_audio_ready(audio_data)
                
            return audio_data
            
        except Exception as e:
            print(f"Error generating speech: {e}")
            return None
            
    def play_audio(self, audio_data: bytes):
        """Plays audio data"""
        if self.is_playing:
            return
            
        def _play():
            try:
                self.is_playing = True
                
                # Create temporary file for audio playback
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    temp_file.write(audio_data)
                    temp_file.flush()
                    
                    # Use system audio player (cross-platform)
                    if os.name == 'nt':  # Windows
                        os.system(f'start /wait "" "{temp_file.name}"')
                    elif os.name == 'posix':  # macOS/Linux
                        os.system(f'afplay "{temp_file.name}" 2>/dev/null || aplay "{temp_file.name}" 2>/dev/null')
                    
                    # Clean up
                    os.unlink(temp_file.name)
                    
            except Exception as e:
                print(f"Error playing audio: {e}")
            finally:
                self.is_playing = False
                
        # Play in separate thread to avoid blocking
        play_thread = threading.Thread(target=_play)
        play_thread.daemon = True
        play_thread.start()
        
    def cleanup(self):
        """Cleanup resources"""
        self.stop_recording()
        if hasattr(self, 'audio'):
            self.audio.terminate()
            
    def __del__(self):
        """Destructor"""
        self.cleanup() 