"""Skill Router: turn the 17 pinned SKILL.md files into executable prompt knowledge.

Each pipeline stage maps to real upstream skill instructions; classification
is honest about what can be automated locally vs. what needs credentials.
"""
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VENDOR=ROOT/'vendor/social-media-skills/skills'

# pipeline stage -> skill ids (order matters: primary first)
STAGE_SKILLS={
 'research':['niche-research'],
 'verification':['post-scorer'],
 'script':['reels-scripting','post-formatter'],
 'hooks':['hook-generator'],
 'thumbnail':['youtube-thumbnail'],
 'social':['post-writer','post-formatter'],
 'pinned':['pinned-comment'],
 'article':['post-formatter'],
 'matrix':['content-matrix'],
 'score':['post-scorer'],
 'voice':['voice-builder'],
 'newsletter':['newsletter-voice'],
 'profile':['profile-optimizer'],
 'carousel':['gemini-carousel'],
 'infographic':['gemini-infographic'],
 'quote':['quote-post'],
 'analytics':['analytics-dashboard'],
}

# honest automation classification (per master-prompt requirements)
CLASSIFICATION={
 'niche-research':'ASSISTED','hook-generator':'AUTOMATED','reels-scripting':'AUTOMATED',
 'post-writer':'AUTOMATED','post-formatter':'AUTOMATED','pinned-comment':'AUTOMATED',
 'content-matrix':'AUTOMATED','post-scorer':'AUTOMATED','youtube-thumbnail':'PARTIAL',
 'voice-builder':'ASSISTED','newsletter-voice':'MANUAL','profile-optimizer':'ASSISTED',
 'analytics-dashboard':'BLOCKED_BY_CREDENTIAL','gemini-carousel':'BLOCKED_BY_CREDENTIAL',
 'gemini-infographic':'BLOCKED_BY_CREDENTIAL','quote-post':'ASSISTED',
 'graphic-designer':'ASSISTED',
}
CLASS_FA={'AUTOMATED':'خودکار','ASSISTED':'کمکی','MANUAL':'دستی','PARTIAL':'نیمه‌خودکار',
          'BLOCKED_BY_CREDENTIAL':'نیازمند Credential'}

def _clean(md):
    """Trim a SKILL.md to its instruction core: drop frontmatter, keep structure."""
    md=re.sub(r'^---.*?---\s*','',md,flags=re.S)
    md=re.sub(r'\n{3,}','\n\n',md)
    return md.strip()

def skill_instructions(skill_id,max_chars=2600):
    """Real instruction text of a pinned skill for prompt injection."""
    for base in (VENDOR,):
        f=base/skill_id/'SKILL.md'
        if f.exists():
            return _clean(f.read_text(encoding='utf-8'))[:max_chars]
        refs=base/skill_id/'references'
    return ''

def skill_brief(stage):
    """Combined instruction context for a pipeline stage (primary skill first)."""
    parts=[]
    for sid in STAGE_SKILLS.get(stage,[]):
        ins=skill_instructions(sid,1800)
        if ins: parts.append(f'### دستورالعمل اسکیل {sid}\n{ins}')
    return '\n\n'.join(parts)

def classification_table():
    rows=[]
    for sid in sorted(CLASSIFICATION):
        ins=skill_instructions(sid,120)
        rows.append({'id':sid,'classification':CLASSIFICATION[sid],
                     'classification_fa':CLASS_FA[CLASSIFICATION[sid]],
                     'exists':bool(ins)})
    return rows
