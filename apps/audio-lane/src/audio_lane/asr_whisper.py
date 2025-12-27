"""
OpenAI Whisper API integration for ASR.
"""

import os
from typing import Dict, List, Optional, Any
from openai import OpenAI


def transcribe_audio(
    audio_path: str,
    language: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transcribe audio using OpenAI Whisper API.
    
    Args:
        audio_path: Path to audio file
        language: Optional language code (e.g., 'en', 'so', 'ak')
        api_key: OpenAI API key (uses OPENAI_API_KEY env var if None)
        
    Returns:
        Dict with keys: text, words, segments, language
    """
    api_key = api_key or os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
    
    client = OpenAI(api_key=api_key)
    
    with open(audio_path, 'rb') as audio_file:
        # Transcribe with word-level timestamps
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"]
        )
    
    # Parse response
    text = transcript.text
    detected_language = getattr(transcript, 'language', language)
    
    # Extract word-level timestamps if available
    words = []
    if hasattr(transcript, 'words') and transcript.words:
        words = [
            {
                'word': w.word,
                'start': w.start,
                'end': w.end,
            }
            for w in transcript.words
        ]
    
    # Extract segment-level timestamps
    segments = []
    if hasattr(transcript, 'segments') and transcript.segments:
        segments = [
            {
                'text': seg.text,
                'start': seg.start,
                'end': seg.end,
            }
            for seg in transcript.segments
        ]
    else:
        # Fallback: use word boundaries if available
        if words:
            current_start = words[0]['start']
            current_text = []
            for word in words:
                current_text.append(word['word'])
                # Split at sentence boundaries (simple heuristic)
                if word['word'].endswith(('.', '!', '?')):
                    segments.append({
                        'text': ' '.join(current_text),
                        'start': current_start,
                        'end': word['end'],
                    })
                    current_text = []
                    if len(words) > words.index(word) + 1:
                        current_start = words[words.index(word) + 1]['start']
            # Add remaining text
            if current_text:
                segments.append({
                    'text': ' '.join(current_text),
                    'start': current_start,
                    'end': words[-1]['end'] if words else 0,
                })
    
    # Determine granularity
    granularity = 'word' if words else 'sentence'
    
    return {
        'text': text,
        'words': words,
        'segments': segments,
        'language': detected_language,
        'granularity': granularity,
    }

