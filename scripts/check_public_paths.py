"""Reject machine-local paths before publishing public resources."""
from pathlib import Path
import re

LOCAL_PATH = re.compile(r"(?i)(?<![a-z0-9])(?:[a-z]:[\\/]|/(?:users|home|mnt|tmp)/[a-z0-9_.-]+|file:[/]{2})")
EXCLUDED = {'.git', 'dist', 'test-runtime', 'local', '__pycache__'}
TEXT_SUFFIXES = {'.json', '.md', '.txt', '.html', '.py', '.yml', '.yaml', '.toml', '.svg', '.js'}

def check_repo(repo):
    violations = []
    for path in sorted(repo.rglob('*')):
        relative = path.relative_to(repo)
        if not path.is_file() or EXCLUDED.intersection(relative.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {'LICENSE', '.gitignore'}:
            continue
        if LOCAL_PATH.search(path.read_text(encoding='utf-8')):
            violations.append(relative.as_posix())
    if violations:
        raise SystemExit('Machine-local paths found in: ' + ', '.join(violations))
    return True

if __name__ == '__main__':
    check_repo(Path(__file__).resolve().parents[1])
    print('Public text files: no machine-local paths')
