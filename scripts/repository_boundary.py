"""Reject a wrong repository or a mixed desktop/mobile source tree before push."""
import argparse
import json
import re
import subprocess
from pathlib import Path

REPOSITORIES = {'public-desktop': 'samuelkcc/AniCanto', 'private-mobile': 'samuelkcc/AniCanto-iOS', 'private-website': 'samuelkcc/anicanto-website'}
PRIVATE_MARKER = '.private-mobile-repository.json'


def remote_repository(url):
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+/[^/]+?)(?:\.git)?/?', url)
    if not match:
        raise ValueError('Unapproved Git remote URL.')
    return match.group(1)


def validate_paths(paths, kind):
    website_files = set(json.loads((Path(__file__).parent / 'website-public-files.json').read_text())['files']) if kind == 'private-website' else set()
    for name in paths:
        p = Path(name)
        lower = name.lower()
        if kind == 'public-desktop':
            if (p.name == PRIVATE_MARKER or any(x.lower() in {'mobile', 'ipad', 'iphone', 'ios', 'devicevalidation'} for x in p.parts)
                    or any(x.lower().endswith(('.xcodeproj', '.xcworkspace', '.xcarchive')) for x in p.parts)
                    or p.suffix.lower() in {'.ipa', '.mobileprovision', '.p12', '.p8', '.keychain-db'}
                    or p.name.startswith(('test_mobile_', 'build_mobile_'))
                    or (p.parts[:1]==('scripts',) and re.search(r'(^|[-_])(mobile|ipad|iphone|ios)([-_.]|$)',p.name,re.I))
                    or p.name in {'test_caption_layers340.py', 'test_text_runtime_boundary345.py'}
                    or (p.suffix == '.swift' and p.name.lower().startswith(('ipad', 'iphone', 'ios', 'storekit', 'iap')))):
                raise ValueError('Private mobile path in the public desktop tree: ' + name)
        elif kind == 'private-mobile':
            if p.parts[0] in {'studio', 'windows', 'Sources', 'Resources'}:
                raise ValueError('Desktop source in the private mobile tree: ' + name)
            if p.suffix.lower() in {'.ipa', '.mobileprovision', '.p12', '.p8', '.keychain-db', '.safetensors', '.gguf', '.litertlm', '.onnx', '.mp4', '.mkv', '.mov', '.wav', '.m4a'}:
                raise ValueError('Media, weights or signing material in the code backup: ' + name)
        elif kind == 'private-website':
            if name not in website_files:
                raise ValueError('Unreviewed path in the website tree: ' + name)
        else:
            raise ValueError('Unknown repository kind.')


def verify(repo, kind, remote_url):
    expected = REPOSITORIES[kind]
    if remote_repository(remote_url).casefold() != expected.casefold():
        raise ValueError('Wrong push destination. Expected ' + expected)
    paths = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '-z']).decode().strip('\0').split('\0')
    paths = [p for p in paths if p]
    validate_paths(paths, kind)
    if kind == 'private-mobile':
        marker = json.loads((repo / PRIVATE_MARKER).read_text())
        if marker != {'repository': expected, 'visibility': 'private', 'codeFamily': 'mobile'}:
            raise ValueError('Missing or changed private mobile boundary marker.')
    remote = json.loads(subprocess.check_output(['gh', 'repo', 'view', expected, '--json', 'isPrivate'], text=True))
    if remote['isPrivate'] != (kind in {'private-mobile', 'private-website'}):
        raise ValueError('Repository visibility does not match its fixed source boundary.')
    return {'repository': expected, 'kind': kind, 'files': len(paths), 'visibilityVerified': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--kind', choices=REPOSITORIES, required=True)
    parser.add_argument('--remote-url', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.repo.resolve(), args.kind, args.remote_url)))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit('Push blocked: ' + str(error))


if __name__ == '__main__':
    main()
