"""One-time encrypted free-token export and public source-cache bootstrap.

The private decryption key stays on the destination VPS. No plaintext token is
written to an artifact, log, command argument, or repository file.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def export(root, destination, public_key, token):
    if not public_key or not token or any(c in token for c in '\n\r\0'):
        raise ValueError('Missing/invalid VPS public key or free Fixtures token')
    root, destination = Path(root), Path(destination)
    files = []
    for path in sorted(root.glob('games/*/data/*')):
        if path.suffix not in ('.json', '.csv'):
            continue
        if path.is_symlink() or path.parent.is_symlink() or path.parent.parent.is_symlink():
            raise ValueError('Source cache symlinks are forbidden')
        if path.is_file():
            files.append(path)
    if not files:
        raise ValueError('No cached source inputs; refusing incomplete bootstrap')
    destination.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory() as temp:
        key = Path(temp) / 'recipient.pem'
        key.write_text(public_key)
        subprocess.run(['openssl', 'pkeyutl', '-encrypt', '-pubin', '-inkey', str(key),
                        '-pkeyopt', 'rsa_padding_mode:oaep', '-pkeyopt', 'rsa_oaep_md:sha256',
                        '-out', str(destination / 'refresh-config.enc')],
                       input=json.dumps({'PANDASCORE_TOKEN': token}).encode(),
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    with tarfile.open(destination / 'source-cache.tar.gz', 'w:gz') as archive:
        for path in files:
            archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
    return len(files)


if __name__ == '__main__':
    count = export(Path.cwd(), sys.argv[1], os.environ.get('VPS_REFRESH_BOOTSTRAP_PUBLIC_KEY'),
                   os.environ.get('PANDASCORE_TOKEN'))
    print('Encrypted server configuration and public source cache ready; files:', count)
