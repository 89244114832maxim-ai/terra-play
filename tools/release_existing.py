#!/usr/bin/env python3
"""Read existing release assets to avoid duplicate game bytes; fail closed."""
import hashlib,json,pathlib,subprocess,sys,tempfile,zipfile
from release_package import is_duplicate
repo,expected,tag=sys.argv[1:]
def gh(*a):return subprocess.run(['gh',*a],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
pages=json.loads(gh('api','--paginate','--slurp',f'repos/{repo}/releases?per_page=100'))
all_releases=[r for page in pages for r in page]
releases=[r for r in all_releases if not r['draft']]
if any(r['tag_name']==tag for r in all_releases): raise SystemExit('tag already exists; refusing overwrite')
# A tag can exist without a release; any ambiguous API failure stops.
ref=subprocess.run(['gh','api',f'repos/{repo}/git/ref/tags/{tag}'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if ref.returncode == 0: raise SystemExit('tag already exists; refusing overwrite')
if b'HTTP 404' not in ref.stderr: raise SystemExit('cannot verify tag absence')
digests=[]
with tempfile.TemporaryDirectory() as tmp:
 for i,r in enumerate(releases):
  matches=[a for a in r['assets'] if a['name']=='terra.zip']
  if len(matches)!=1 or matches[0]['size']>50_000_000: raise SystemExit('cannot establish existing release content')
  dest=pathlib.Path(tmp)/str(i);dest.mkdir()
  gh('release','download',r['tag_name'],'--repo',repo,'--pattern','terra.zip','--dir',str(dest))
  with zipfile.ZipFile(dest/'terra.zip') as z:
   entries=[x for x in z.infolist() if x.filename=='terra.html']
   if len(entries)!=1 or entries[0].file_size>25_000_000: raise SystemExit('invalid existing game archive')
   digests.append(hashlib.sha256(z.read(entries[0])).hexdigest())
if is_duplicate(expected,digests): raise SystemExit('game already released; no new release')
