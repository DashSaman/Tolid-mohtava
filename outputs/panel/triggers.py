"""Approval -> next real step. Idempotent by content id + revision.

Publish approval produces a DRY RUN package only: no external service is
called, no credentials are used. External publishing stays blocked until
the user explicitly connects an adapter (out of current scope).
"""
import json
from pathlib import Path

PLATFORMS={'YouTube','YouTube Shorts','Instagram','Instagram Reels','Telegram','Facebook','LinkedIn','Website'}
DRYRUN_NOTE='DRY RUN — هیچ انتشار خارجی انجام نشد؛ این بسته فقط برای بازبینی شماست.'

def format_note(platform):
    table={
     'YouTube':'توضیح کامل + فصل‌بندی + لینک منابع؛ CTA اشتراک در پایان توضیح.',
     'YouTube Shorts':'عمودی ۹:۱۶، هوک در ۲ ثانیه اول، CTA به ویدیوی کامل.',
     'Instagram':'کپشن کوتاه‌تر از پست لینکدین، هشتگ‌های مرتبط فارسی/انگلیسی، CTA ذخیره و اشتراک.',
     'Instagram Reels':'عمودی ۹:۱۶، متن روی ویدیو، CTA به پست کامل در بیو.',
     'Telegram':'متن روان با پاراگراف‌های کوتاه، لینک کامل ویدیو/مقاله، بدون هشتگ انبوه.',
     'Facebook':'متن گفتاری‌تر، لینک با پیش‌نمایش، CTA نظر و اشتراک.',
     'LinkedIn':'ساختار حرفه‌ای، ۳ اول درس‌های کلیدی، CTA نظر حرفه‌ای.',
     'Website':'مقاله کامل SEO با تیتربندی، لینک داخلی به مرتبط‌ها و منبع خارجی معتبر.',
    }
    return table.get(platform,'پلتفرم نامشخص؛ نسخه مستقل هر پلتفرم بسازید، کپی کورکورانه ممنوع.')

def build_dryrun(store,content_id,revision):
    item=store.get(content_id)
    if not item: raise ValueError('محتوا پیدا نشد.')
    if revision!=item['revision']: raise ValueError('این تأیید برای نسخه قدیمی است؛ نسخه فعلاً تغییر کرده است.')
    brands={b:('tehnet.ir' if b=='tehran-network' else 'mytel.one') for b in item['brands']}
    package={'mode':'dry_run','note':DRYRUN_NOTE,'content_id':content_id,'revision':revision,
             'title':item['title'],'platform':item.get('platform',''),
             'brands':brands,'generated_at':None,'sections':{}}
    body=item.get('body') or ''
    package['sections']={
      'main_copy':body[:1200] if body else '(متنی ثبت نشده)',
      'platform_adaptation':format_note(item.get('platform','')),
      'pinned_comment':'یک پرسش مشارکتی + CTA نرم (تولید با اسکیل pinned-comment پس از تأیید شما).',
      'seo_baseline':('عنوان و متا از نسخه تأییدشده؛ بررسی intent و کلمه کلیدی پیش از انتشار لازم است.'
                       if item.get('platform')=='Website' else 'برای وب، نسخه مقاله‌ای مستقل از transcript لازم است.'),
    }
    package['warnings']=[]
    if not body.strip(): package['warnings'].append('متن اصلی این نسخه خالی است.')
    if not item.get('transcript','').strip(): package['warnings'].append('متن واقعی ضبط ثبت نشده است.')
    return package

def publish_dryrun_handler(ctx):
    """Job handler: approved publish -> inspectable dry-run artifact."""
    store=ctx.services['store']; root=Path(ctx.services.get('dryrun_root') or 'data/dryrun')
    payload=ctx.payload
    package=build_dryrun(store,payload['content_id'],payload['revision'])
    package['generated_at']=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
    root.mkdir(parents=True,exist_ok=True)
    out=root/f"{payload['content_id']}_rev{payload['revision']}.json"
    out.write_text(json.dumps(package,ensure_ascii=False,indent=1),encoding='utf-8')
    ctx.log('بسته dry-run ساخته شد؛ هیچ درخواست خارجی ارسال نشد.')
    return {'artifact':str(out),'mode':'dry_run','revision':payload['revision'],
            'warnings':package['warnings'],'platform':package['platform']}

def on_publish_approved(jm,content_id,revision):
    """Exactly one active dry-run per content+revision."""
    return jm.enqueue('publish_dryrun',{'content_id':content_id,'revision':revision},
                      idempotency_key=f'publish_dryrun:{content_id}:{revision}')
