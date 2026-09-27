"""Worker handler registry: job kind -> real work. No simulated success."""
from transcribe import transcribe_audio_handler

def build_handlers():
    return {'transcribe_audio': transcribe_audio_handler}
