#!/usr/bin/env python3
"""Create and validate a minimal offline archive; never publish anything."""
import argparse, hashlib, json, pathlib, re, zipfile

def sha(data): return hashlib.sha256(data).hexdigest()
def validate_context(event, current, tag):
    run=event.get('workflow_run',{})
    if run.get('conclusion')!='success' or run.get('head_branch')!='main' or run.get('head_sha')!=current:
        raise ValueError('deploy is unsuccessful, untrusted, or stale')
    if not re.fullmatch(r'[0-9a-f]{40}',current): raise ValueError('invalid SHA')
    if not re.fullmatch(r'build-\d{8}-\d{4}',tag): raise ValueError('invalid tag')

def package(root, out):
    root=pathlib.Path(root);out=pathlib.Path(out)
    if out.exists(): raise ValueError('output exists')
    files={'terra.html': root/'play/index.html', 'credits.html':root/'credits.html'}
    data={}
    for name,path in files.items():
        if path.is_symlink() or not path.is_file(): raise ValueError('missing or linked input')
        data[name]=path.read_bytes()
    data['README.txt']='Распакуйте архив и откройте terra.html. Авторы и лицензии: credits.html.\n'.encode()
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,content in data.items():
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,content,compresslevel=9)
    verify_archive(out, data)
    return {'html_sha256':sha(data['terra.html']),'zip_sha256':sha(out.read_bytes())}

def verify_archive(path, data):
    with zipfile.ZipFile(path) as z:
        if z.namelist()!=list(data) or any(z.read(n)!=v for n,v in data.items()):
            raise ValueError('archive verification failed')


def is_duplicate(game_digest, existing_digests):
    if not re.fullmatch(r'[0-9a-f]{64}', game_digest): raise ValueError('invalid digest')
    if any(not re.fullmatch(r'[0-9a-f]{64}', d) for d in existing_digests): raise ValueError('unknown existing digest')
    return game_digest in existing_digests


def main():
    p=argparse.ArgumentParser();p.add_argument('--event',required=True);p.add_argument('--current',required=True);p.add_argument('--tag',required=True);p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    validate_context(json.loads(pathlib.Path(a.event).read_text()),a.current,a.tag)
    print(json.dumps(package(a.root,a.output)))
if __name__=='__main__':main()
