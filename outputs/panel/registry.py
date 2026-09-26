"""Report actual local/global discovery; a clone is not an installation."""
from pathlib import Path
import hashlib,json,os
ROOT=Path(__file__).resolve().parents[2]
def skill_registry():
    rows=json.loads((ROOT/'outputs/panel/skills.json').read_text(encoding='utf-8'))
    locations=[ROOT/'.agents/skills',Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'skills']
    for row in rows:
        row['installed']=False
        row['skill_path']=''
        for folder in locations:
            file=folder/row['id']/'SKILL.md'
            if file.is_file():
                row['installed']=hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
                row['skill_path']=str(file)
                break
    return rows
