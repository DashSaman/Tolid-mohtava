"""Worker handler registry: job kind -> real work. No simulated success."""
from transcribe import transcribe_audio_handler
from editing import edit_detect_handler
from render import render_cut_handler
from shorts import render_short_handler
from publishing import website_publish_handler
from ai_jobs import (research_topic_handler, technical_verification_handler, generate_script_handler,
    generate_hooks_handler, generate_title_packages_handler, generate_social_handler,
    generate_article_handler, generate_pinned_handler, content_pipeline_handler)
from triggers import publish_dryrun_handler

def build_handlers():
    return {'transcribe_audio': transcribe_audio_handler,
            'edit_detect': edit_detect_handler,
            'render_cut': render_cut_handler,
            'render_short': render_short_handler,
            'publish_dryrun': publish_dryrun_handler,
            'website_publish': website_publish_handler,
            'research_topic': research_topic_handler,
            'technical_verification': technical_verification_handler,
            'generate_script': generate_script_handler,
            'generate_hooks': generate_hooks_handler,
            'generate_title_packages': generate_title_packages_handler,
            'generate_social': generate_social_handler,
            'generate_article': generate_article_handler,
            'generate_pinned': generate_pinned_handler,
            'content_pipeline': content_pipeline_handler}
