from pathlib import Path
from datetime import datetime
import sqlite3
root=Path(__file__).resolve().parent
dest=root.parent/'backups'
dest.mkdir(exist_ok=True)
source=root/'data/content.sqlite'
if not source.exists(): raise SystemExit('Panel database does not exist yet.')
file=dest/('content-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite')
a=sqlite3.connect(str(source)); b=sqlite3.connect(str(file))
try: a.backup(b)
finally: b.close(); a.close()
print(file)
