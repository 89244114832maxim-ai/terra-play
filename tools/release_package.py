#!/usr/bin/env python3
"""Dry-run packaging and release planning; never publish or modify releases."""
import argparse, hashlib, json, pathlib, re, zipfile

MAX_GAME=100_000_000
MAX_CREDITS=1_000_000
MAX_ZIP=100_000_000
README='Распакуйте архив и откройте terra.html. Авторы и лицензии: credits.html.\n'.encode()
REQUIRED=('game-icons.net','creativecommons.org/licenses/by/3.0/','перекраш','delapouite','guard13007','lorc','sbed','skoll','zeromancer','atomicrealm.itch.io')
def sha(data): return hashlib.sha256(data).hexdigest()
def validate_context(event, current, tag):
    run=event.get('workflow_run',{})
    if run.get('conclusion')!='success' or run.get('head_branch')!='main' or run.get('head_sha')!=current: raise ValueError('deploy unsuccessful, untrusted, or stale')
    if not re.fullmatch(r'[0-9a-f]{40}',current): raise ValueError('invalid SHA')
    if not re.fullmatch(r'build-\d{8}-\d{4}',tag): raise ValueError('invalid tag')

def read_input(root, relative, limit):
    root=pathlib.Path(root).resolve(strict=True); path=root
    for component in pathlib.PurePosixPath(relative).parts:
        path=path/component
        if path.is_symlink(): raise ValueError('symlink input or parent')
    if not path.is_file() or path.stat().st_size>limit: raise ValueError('input missing or too large')
    return path.read_bytes()

def package(root, out):
    out=pathlib.Path(out)
    if out.exists(): raise ValueError('output exists')
    game=read_input(root,'play/index.html',MAX_GAME); credits=read_input(root,'credits.html',MAX_CREDITS)
    text=credits.decode('utf-8')
    if any(x not in text for x in REQUIRED): raise ValueError('required credits missing')
    data={'terra.html':game,'credits.html':credits,'README.txt':README}
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,content in data.items():
            info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,content,compresslevel=9)
    verify_archive(out,data)
    return {n:sha(v) for n,v in data.items()} | {'zip_sha256':sha(out.read_bytes())}

def verify_archive(path, expected):
    if pathlib.Path(path).stat().st_size>MAX_ZIP: raise ValueError('archive too large')
    with zipfile.ZipFile(path) as z:
        if z.namelist()!=list(expected): raise ValueError('archive entries mismatch')
        limits={'terra.html':MAX_GAME,'credits.html':MAX_CREDITS,'README.txt':10000}
        if any(z.getinfo(n).file_size>limits[n] for n in expected): raise ValueError('expanded input too large')
        if any(z.read(n)!=v for n,v in expected.items()): raise ValueError('archive content mismatch')

def compare_latest(existing, candidate):
    # Unknown/legacy ZIP is not considered equivalent; no implicit overwrites.
    keys=('terra.html','credits.html','README.txt')
    return all(existing.get(k)==candidate.get(k) and re.fullmatch(r'[0-9a-f]{64}',candidate.get(k,'')) for k in keys)

def draft_plan(tag_sha, expected_sha, asset_digests, expected_assets):
    if tag_sha not in (None,expected_sha): raise ValueError('tag points elsewhere')
    for name,digest in asset_digests.items():
        if name not in expected_assets or expected_assets[name]!=digest: raise ValueError('unexpected or mismatched draft asset')
    return sorted(set(expected_assets)-set(asset_digests))

def main():
    p=argparse.ArgumentParser();p.add_argument('--event',required=True);p.add_argument('--current',required=True);p.add_argument('--tag',required=True);p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    validate_context(json.loads(pathlib.Path(a.event).read_text()),a.current,a.tag)
    print(json.dumps(package(a.root,a.output)))
if __name__=='__main__':main()
