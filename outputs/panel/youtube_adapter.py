"""YouTube through Google's maintained SDK. Uploads stay private and approval-gated."""
import os,sqlite3,time
from pathlib import Path
from jobs import DependencyMissing,JobCancelled

def connection_status(oauth):
    configured=bool(os.environ.get('YOUTUBE_CLIENT_ID') and os.environ.get('YOUTUBE_CLIENT_SECRET'))
    with oauth.connect() as c:
        row=c.execute('SELECT access_token,refresh_token FROM oauth_tokens WHERE provider=?',('youtube',)).fetchone()
    linked=bool(oauth.get_token('youtube')) or bool(row and row[1]) or bool(os.environ.get('YOUTUBE_REFRESH_TOKEN'))
    return {'configured':configured,'connected':configured and linked,
            'detail':'حساب متصل است؛ آپلود تنها پس از تأیید و به‌صورت خصوصی انجام می‌شود.' if configured and linked else
                     ('برنامه تنظیم شده؛ دکمهٔ اتصال حساب را بزنید.' if configured else 'Client ID و Client Secret گوگل تنظیم نشده؛ آماده‌بودن کانال کافی نیست.')}

def client(oauth):
    if not connection_status(oauth)['connected']:
        raise DependencyMissing('YouTube: ابتدا برنامهٔ Google و اتصال حساب را کامل کنید (BLOCKED_BY_CREDENTIAL).')
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        raise DependencyMissing('کتابخانهٔ رسمی Google API نصب نیست؛ تصویر Docker را به‌روز کنید.')
    with oauth.connect() as c:
        row=c.execute('SELECT access_token,refresh_token,scope FROM oauth_tokens WHERE provider=?',('youtube',)).fetchone()
    creds=Credentials(oauth.get_token('youtube'),refresh_token=(row[1] if row else '') or os.environ.get('YOUTUBE_REFRESH_TOKEN'),
        token_uri='https://oauth2.googleapis.com/token',client_id=os.environ['YOUTUBE_CLIENT_ID'],client_secret=os.environ['YOUTUBE_CLIENT_SECRET'])
    if not creds.token:
        try:creds.refresh(Request())
        except Exception:raise DependencyMissing('اتصال یوتیوب منقضی شده یا اجازهٔ دسترسی رد شد؛ حساب را دوباره وصل کنید.')
        oauth.save_token('youtube',creds.token,creds.refresh_token,(row[2] if row else ''),3600)
    return build('youtube','v3',credentials=creds,cache_discovery=False)

def channel_statistics(oauth):
    out=client(oauth).channels().list(part='statistics',mine=True).execute()
    rows=out.get('items') or []
    if not rows:raise DependencyMissing('کانالی برای حساب متصل پیدا نشد.')
    row=rows[0];s=row.get('statistics') or {}
    metrics={}
    for key,api in [('views','viewCount'),('subscribers_total','subscriberCount'),('videos_total','videoCount')]:
        if api in s:metrics[key]=int(s[api])
    return row['id'],metrics

def youtube_upload_handler(ctx):
    if not ctx.payload.get('approved'):
        return {'waiting_approval':True,'question':'این نسخهٔ نهایی به حساب YouTube متصل، به‌صورت خصوصی آپلود شود؟ انتشار عمومی انجام نمی‌شود.'}
    store=ctx.services['store'];item=store.get(ctx.payload.get('content_id'))
    revision=ctx.payload.get('revision')
    if item['revision']!=revision:raise ValueError('نسخهٔ پروژه تغییر کرده؛ درخواست جدید با نسخهٔ فعلی لازم است.')
    if item.get('publish_status')!='approved':raise ValueError('تأیید انتشار این نسخه هنوز ثبت نشده است.')
    render=ctx.services['renders'].get(ctx.payload.get('render_id'))
    if not render or render['kind']!='final':raise ValueError('یک رندر نهایی معتبر انتخاب کنید.')
    media=ctx.services['media'].get(render['media_id'])
    if not media or media['content_id']!=item['id']:raise ValueError('رندر متعلق به این پروژه نیست.')
    if not Path(render['path']).is_file():raise ValueError('فایل رندر نهایی پیدا نشد.')
    with store.connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS youtube_uploads(content_id TEXT,revision INTEGER,render_id TEXT,video_id TEXT,PRIMARY KEY(content_id,revision,render_id))')
        old=c.execute('SELECT video_id FROM youtube_uploads WHERE content_id=? AND revision=? AND render_id=?',(item['id'],revision,render['id'])).fetchone()
    if old:return {'video_id':old[0],'privacy':'private','reused':True}
    youtube=client(ctx.services['oauth'])
    from googleapiclient.http import MediaFileUpload
    upload=MediaFileUpload(render['path'],mimetype='video/mp4',chunksize=8*1024*1024,resumable=True)
    request=youtube.videos().insert(part='snippet,status',body={'snippet':{'title':item['title'][:100],
        'description':(item.get('body') or '').encode('utf-8')[:5000].decode('utf-8','ignore'),'categoryId':'27'},'status':{'privacyStatus':'private'}},media_body=upload)
    response=None
    try:
        while response is None:
            if ctx.cancelled():raise JobCancelled()
            progress,response=request.next_chunk(num_retries=2)
            if progress:ctx.progress(5+90*progress.progress())
    finally:
        upload.stream().close()
    if not response or not response.get('id'):raise RuntimeError('YouTube شناسهٔ ویدیو برنگرداند؛ آپلود تأیید نشد.')
    with store.connect() as c:
        c.execute('INSERT INTO youtube_uploads VALUES(?,?,?,?)',(item['id'],revision,render['id'],response['id']))
    ctx.log('آپلود خصوصی کامل شد؛ انتشار عمومی را در YouTube Studio بازبینی کنید.')
    return {'video_id':response['id'],'privacy':'private','studio_url':'https://studio.youtube.com/video/'+response['id']+'/edit'}
