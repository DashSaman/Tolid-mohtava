"""Check maintained local documentation links, image files and absent runtime data."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
files=[ROOT/'README.md',ROOT/'README.en.md',*list((ROOT/'docs').glob('*.md'))]
errors=[];checked=0
for f in files:
    text=f.read_text(encoding='utf-8')
    links=re.findall(r'\]\(([^\s)]+)\)',text)+re.findall(r'<img[^>]+src="([^"]+)"',text)
    for link in links:
        if '://' in link or link.startswith('#'):continue
        target=(f.parent/link.split('#')[0]).resolve()
        if not target.exists():errors.append(str(f.relative_to(ROOT))+': '+link)
        checked+=1
for name in ('dashboard.png','mobile.png','skills.png','approval-demo.png'):
    p=ROOT/'docs/images'/name
    if not p.exists() or p.stat().st_size<1000:errors.append('Missing/empty screenshot: '+name)
if errors:raise SystemExit('\n'.join(errors))
print(f'PASS: {checked} relative documentation/image links and 4 screenshots.')
