"""Worker handler registry: job kind -> real work. No simulated success."""
from transcribe import transcribe_audio_handler
from editing import edit_detect_handler
from render import render_cut_handler
from triggers import publish_dryrun_handler

def build_handlers():
    return {'transcribe_audio': transcribe_audio_handler,
            'edit_detect': edit_detect_handler,
            'render_cut': render_cut_handler,
            'publish_dryrun': publish_dryrun_handler}
