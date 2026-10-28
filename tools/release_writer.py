#!/usr/bin/env python3
"""Deliver a verified package via a resumable draft release."""
import hashlib,json,pathlib,re,subprocess,tempfile,zipfile
from release_package import MAX_ZIP,MAX_GAME,MAX_CREDITS,README,sha

class GitHub:
 def __init__(self,repo): self.repo=repo
 def api(self,path,*args,missing=False):
  p=subprocess.run(['gh','api',f'repos/{self.repo}/{path}',*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  if p.returncode:
   if missing and b'HTTP 404' in p.stderr:return None
   raise RuntimeError('GitHub API request failed')
  return json.loads(p.stdout)
 def main_sha(self):return self.api('git/ref/heads/main')['object']['sha']
 def ref_sha(self,tag):
  ref=self.api('git/ref/tags/'+tag,missing=True)
  if ref is None:return None
  obj=ref['object']
  for _ in range(5):
   if obj['type']=='commit':return obj['sha']
   if obj['type']!='tag':raise ValueError('unknown tag object')
   obj=self.api('git/tags/'+obj['sha'])['object']
  raise ValueError('tag nesting limit')
 def create_ref(self,tag,commit): self.api('git/refs','-X','POST','-f','ref=refs/tags/'+tag,'-f','sha='+commit)
 def latest(self):return self.api('releases/latest',missing=True)
 def by_id(self,rid):return self.api('releases/'+str(rid))
 def releases(self):
  pages=json.loads(subprocess.check_output(['gh','api','--paginate','--slurp',f'repos/{self.repo}/releases?per_page=100'],text=True))
  return [r for page in pages for r in page]
 def create_draft(self,tag,commit,body):return self.api('releases','-X','POST','-f','tag_name='+tag,'-f','target_commitish='+commit,'-f','name=Терра — сборка','-f','body='+body,'-F','draft=true')
 def upload(self,tag,path):subprocess.run(['gh','release','upload',tag,str(path),'--repo',self.repo],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 def publish(self,rid):self.api('releases/'+str(rid),'-X','PATCH','-F','draft=false','-f','make_latest=true')
 def download(self,tag,name,directory):subprocess.run(['gh','release','download',tag,'--repo',self.repo,'--pattern',name,'--dir',str(directory)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

def expected_assets(paths):return {p.name:{'digest':'sha256:'+sha(p.read_bytes()),'size':p.stat().st_size} for p in paths}
def verify_assets(release, expected, complete):
 assets=release.get('assets',[]); names=[a['name'] for a in assets]
 if len(names)!=len(set(names)) or any(n not in expected for n in names):raise ValueError('unexpected or duplicate release asset')
 for a in assets:
  x=expected[a['name']]
  if a.get('digest')!=x['digest'] or a.get('size')!=x['size'] or a.get('state')!='uploaded':raise ValueError('asset mismatch or digest unavailable')
 if complete and set(names)!=set(expected):raise ValueError('missing release asset')
 return set(expected)-set(names)

def latest_matches(api,release,game,credits):
 if not release:return False
 matches=[a for a in release.get('assets',[]) if a['name']=='terra.zip']
 if len(matches)!=1:return False
 a=matches[0]
 if a.get('state')!='uploaded' or a.get('size',MAX_ZIP+1)>MAX_ZIP or not re.fullmatch(r'sha256:[0-9a-f]{64}',a.get('digest') or ''):raise ValueError('latest asset digest unavailable')
 with tempfile.TemporaryDirectory() as t:
  api.download(release['tag_name'],'terra.zip',t);p=pathlib.Path(t)/'terra.zip'
  if p.stat().st_size!=a['size'] or 'sha256:'+sha(p.read_bytes())!=a['digest']:raise ValueError('latest asset readback mismatch')
  with zipfile.ZipFile(p) as z:
   names=z.namelist()
   if len(names)!=len(set(names)) or any(n not in ('terra.html','credits.html','README.txt') for n in names):raise ValueError('unexpected latest archive entries')
   if 'terra.html' not in names or z.getinfo('terra.html').file_size>MAX_GAME:raise ValueError('invalid latest archive')
   if 'credits.html' not in names or 'README.txt' not in names:return False
   if z.getinfo('credits.html').file_size>MAX_CREDITS or z.getinfo('README.txt').file_size>10000:raise ValueError('latest archive too large')
   return z.read('terra.html')==game and z.read('credits.html')==credits and z.read('README.txt')==README

def deliver(api,commit,tag,paths,game,credits):
 if not re.fullmatch(r'[0-9a-f]{40}',commit) or not re.fullmatch(r'build-\d{8}-\d{4}',tag):raise ValueError('invalid commit or tag')
 expected=expected_assets(paths); body='Сборка игры для браузера и автономного запуска.\n\nКоммит: '+commit
 if api.main_sha()!=commit:raise ValueError('stale main')
 if latest_matches(api,api.latest(),game,credits):return 'already published'
 tagged=[r for r in api.releases() if r['tag_name']==tag]
 if len(tagged)>1:raise ValueError('duplicate release tag')
 release=tagged[0] if tagged else None
 tag_sha=api.ref_sha(tag)
 if tag_sha not in (None,commit):raise ValueError('tag collision')
 if release:
  if not release.get('draft') or release.get('body')!=body:raise ValueError('existing release is not matching draft')
 else:
  if tag_sha is not None:raise ValueError('existing tag without matching draft')
  release=api.create_draft(tag,commit,body)
 if not release.get('draft') or release.get('tag_name')!=tag or release.get('body')!=body:raise ValueError('draft creation mismatch')
 if api.ref_sha(tag) is None:api.create_ref(tag,commit)
 if api.ref_sha(tag)!=commit:raise ValueError('tag race')
 missing=verify_assets(release,expected,False)
 for p in paths:
  if p.name in missing:api.upload(tag,p)
 release=api.by_id(release['id'])
 if not release or not release.get('draft') or release.get('tag_name')!=tag or release.get('body')!=body:raise ValueError('draft changed')
 verify_assets(release,expected,True)
 if api.ref_sha(tag)!=commit or api.main_sha()!=commit:raise ValueError('tag or main changed before publish')
 api.publish(release['id'])
 result=api.by_id(release['id'])
 if result.get('draft') or result.get('tag_name')!=tag:raise ValueError('published release readback mismatch')
 verify_assets(result,expected,True)
 if api.ref_sha(tag)!=commit:raise ValueError('published tag mismatch')
 return 'published'
