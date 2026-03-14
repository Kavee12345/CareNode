"""
Voice service for Speech-to-Text and Text-to-Speech using free libraries.

STT: SpeechRecognition (uses Google's free web speech API, no API key needed)
TTS: gTTS (Google Translate TTS, free, no API key needed)
"""
import io
import re
import asyncio
from typing import Optional

import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment

from app.config import settings


async def transcribe_audio(audio_bytes: bytes, content_type: str) -> str:
    """
    Transcribe audio bytes to text using SpeechRecognition.

    Converts any audio format to WAV via pydub, then uses Google's
    free speech recognition API (no API key required).

    Args:
        audio_bytes: Raw audio file bytes
        content_type: MIME type of the audio (e.g. audio/webm, audio/wav)

    Returns:
        Transcribed text string

    Raises:
        ValueError: If transcription fails or audio is unrecognizable
    """
    # Map MIME types to pydub format strings
    mime_to_format = {
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/mp4": "mp4",
        "audio/m4a": "m4a",
        "audio/flac": "flac",
    }

    fmt = mime_to_format.get(content_type)
    if not fmt:
        raise ValueError(f"Unsupported audio format: {content_type}")

    def _do_transcribe() -> str:
        # Convert to WAV using pydub (requires ffmpeg)
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
        wav_buffer = io.BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        wav_buffer.seek(0)

        # Use SpeechRecognition
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_buffer) as source:
            audio_data = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio_data, language=settings.stt_language)
        except sr.UnknownValueError:
            raise ValueError("Could not understand the audio. Please try again.")
        except sr.RequestError as e:
            raise ValueError(f"Speech recognition service error: {e}")

        if not text.strip():
            raise ValueError("No speech detected in the audio. Please try again.")

        return text.strip()

    # Run in thread pool since pydub and SpeechRecognition are blocking
    return await asyncio.get_event_loop().run_in_executor(None, _do_transcribe)


def _clean_text_for_speech(text: str) -> str:
    """Remove markdown formatting and special characters for cleaner TTS output."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)  # italic
    text = re.sub(r"`(.+?)`", r"\1", text)  # inline code
    text = re.sub(r"#{1,6}\s*", "", text)  # headers
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)  # links
    text = re.sub(r"[-*]\s+", "", text)  # bullet points
    text = re.sub(r"\n{2,}", ". ", text)  # multiple newlines
    text = text.replace("\n", " ")
    return text.strip()


async def synthesize_speech(text: str) -> bytes:
    """
    Convert text to speech using gTTS (free, no API key).

    Args:
        text: Plain text to synthesize

    Returns:
        MP3 audio bytes

    Raises:
        ValueError: If synthesis fails
    """
    cleaned_text = _clean_text_for_speech(text)

    if not cleaned_text:
        raise ValueError("No text to synthesize.")

    def _do_synthesize() -> bytes:
        tts = gTTS(text=cleaned_text, lang=settings.tts_language)
        mp3_buffer = io.BytesIO()
        tts.write_to_fp(mp3_buffer)
        mp3_buffer.seek(0)
        return mp3_buffer.read()

    # Run in thread pool since gTTS makes a network call
    return await asyncio.get_event_loop().run_in_executor(None, _do_synthesize)
