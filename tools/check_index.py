"""Validate the documentation-only inventory and canonical project destinations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    '.gitattributes', '.gitignore', '.github/workflows/checks.yml',
    'CONTRIBUTING.md', 'README.md', 'THIRD_PARTY.md',
    'docs/ENGINEERING_NOTES.md', 'docs/PUBLICATION_SCOPE.md',
    'publication-policy.json', 'tests/test_publication_policy.py',
    'tools/check_publication.py', 'tools/check_index.py',
}
CANONICAL = {
    'FracLogGPT-Lite', 'MemLab', 'Recruitment-Text-Classification', 'JSP-UI-Prototype',
}
LINK = re.compile(r'!?\[[^\]\n]*\]\(([^\s)]+)\)')


def command(*arguments: str) -> bytes:
    result = subprocess.run(arguments, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=60)
    if result.returncode:
        raise ValueError('Read-only command failed: ' + arguments[0])
    return result.stdout


def gh(endpoint: str):
    return json.loads(command('gh', 'api', endpoint))


def check(remote: bool = False) -> None:
    tracked = set(command('git', 'ls-files', '-z').decode('utf-8').strip('\0').split('\0'))
    if tracked != EXPECTED:
        raise ValueError(f'Index inventory changed: extra={sorted(tracked - EXPECTED)}, missing={sorted(EXPECTED - tracked)}')
    if (ROOT / 'projects').exists():
        raise ValueError('Project source must be maintained in its standalone repository')
    policy = json.loads((ROOT / 'publication-policy.json').read_text(encoding='utf-8'))
    if policy['approved_project_roots'] or policy['approved_project_directories'] or policy['approved_project_root_names']:
        raise ValueError('The deployed publication policy must not allow project subtrees')
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    for name in CANONICAL:
        if f'https://github.com/Darssal/{name})' not in readme:
            raise ValueError('Missing canonical README entry: ' + name)

    targets: set[tuple[str, str]] = set()
    local_count = 0
    for name in sorted(EXPECTED):
        if not name.endswith('.md'):
            continue
        for raw in LINK.findall((ROOT / name).read_text(encoding='utf-8')):
            url = urlsplit(raw)
            if not url.scheme and not url.netloc:
                if not url.path:
                    continue
                target = (ROOT / name).parent / unquote(url.path)
                if not target.exists() or not target.resolve().is_relative_to(ROOT.resolve()):
                    raise ValueError(f'Broken or out-of-root document link in {name}: {raw}')
                local_count += 1
            elif url.netloc == 'github.com':
                parts = unquote(url.path).strip('/').split('/')
                if len(parts) >= 2 and parts[0] == 'Darssal' and parts[1] in CANONICAL:
                    if len(parts) == 2:
                        targets.add((parts[1], ''))
                    elif len(parts) >= 5 and parts[2:4] == ['blob', 'main']:
                        targets.add((parts[1], '/'.join(parts[4:])))
                    else:
                        raise ValueError(f'Unexpected canonical link in {name}: {raw}')
                if '../projects/' in raw:
                    raise ValueError('Old Collection project link remains')
    print(f'Index inventory: {len(tracked)} maintenance/document files; no project source')
    print(f'Links: {local_count} local references and {len(targets)} canonical repository/file targets')
    if remote:
        for name in sorted(CANONICAL):
            metadata = gh(f'repos/Darssal/{name}')
            if metadata['private'] or metadata['default_branch'] != 'main':
                raise ValueError('Expected a public canonical repository with main: ' + name)
            tree = gh(f'repos/Darssal/{name}/git/trees/main?recursive=1')
            if tree.get('truncated'):
                raise ValueError('Canonical tree response was truncated: ' + name)
            blobs = {entry['path'] for entry in tree['tree'] if entry['type'] == 'blob'}
            for repo, path in targets:
                if repo == name and path and path not in blobs:
                    raise ValueError(f'Canonical linked file is missing: {repo}/{path}')
            print(f'Public canonical repository verified: {name} @ {tree["sha"]}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remote', action='store_true', help='Read public GitHub metadata and file trees with gh')
    args = parser.parse_args()
    check(args.remote)


if __name__ == '__main__':
    main()
