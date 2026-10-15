"""Offline SQLite restore; caller must stop the panel before invoking this."""
import os,sqlite3,sys
from pathlib import Path

def restore(source,target):
    source=Path(source);target=Path(target)
    if not source.is_file():raise ValueError('Backup file is missing.')
    if source.resolve()==target.resolve():raise ValueError('Source and destination must differ.')
    temporary=target.with_name(target.name+'.restore-tmp')
    if temporary.exists():raise ValueError('A previous temporary restore exists; inspect it before retrying.')
    incoming=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        if incoming.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup integrity failed.')
        incoming.execute('SELECT COUNT(*) FROM content').fetchone()
        outgoing=sqlite3.connect(temporary)
        try:
            incoming.backup(outgoing)
            if outgoing.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Restored snapshot integrity failed.')
        finally:outgoing.close()
    finally:incoming.close()
    for suffix in ('-wal','-shm'):
        sidecar=Path(str(target)+suffix)
        if sidecar.exists():sidecar.unlink()
    os.replace(temporary,target)
    print('RESTORE verified: integrity ok')

if __name__=='__main__':restore(sys.argv[1],sys.argv[2])
