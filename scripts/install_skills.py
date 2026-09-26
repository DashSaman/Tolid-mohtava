"""Install the pinned, vendored skills locally; preserve every existing destination."""
from pathlib import Path
import argparse, hashlib, json, os, shutil

ROOT=Path(__file__).resolve().parents[1]
def install(destination):
    source=ROOT/'vendor/social-media-skills/skills'
    expected=json.loads((ROOT/'outputs/installation-manifest.json').read_text(encoding='utf-8'))
    for entry in expected['files']:
        p=ROOT/entry['path']
        if hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('Vendored source checksum mismatch: '+entry['path'])
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=True)
    results=[]
    for folder in sorted(source.iterdir()):
        if not (folder/'SKILL.md').is_file():continue
        target=destination/folder.name
        if target.exists() or target.is_symlink():
            results.append((folder.name,'preserved'));continue
        shutil.copytree(folder,target)
        results.append((folder.name,'installed'))
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--global',dest='global_install',action='store_true',help='Use CODEX_HOME/skills instead of .agents/skills')
    group.add_argument('--dest',type=Path,help='Explicit destination directory')
    a=p.parse_args()
    destination=a.dest or ((Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'skills') if a.global_install else ROOT/'.agents/skills')
    for name,status in install(destination):print(f'{status}: {name}')
    print('Open a new Codex turn in this repository. Existing skill directories were preserved.')
