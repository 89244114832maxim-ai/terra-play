import pathlib,tempfile,unittest,zipfile
from release_writer import deliver,sha
from release_package import README
S='a'*40; TAG='build-20261028-0030'; BODY='Сборка игры для браузера и автономного запуска.\n\nКоммит: '+S
class Fake:
 def __init__(self):self.main=S;self.ref=None;self.rel=None;self.previous=None;self.uploads=[];self.created=0;self.published=0;self.race=False;self.zipbytes=None
 def main_sha(self):return self.main
 def ref_sha(self,tag):return self.ref
 def create_ref(self,tag,commit):self.ref='b'*40 if self.race else commit
 def latest(self):return self.previous
 def releases(self):return [self.rel] if self.rel else []
 def create_draft(self,tag,commit,body):self.created+=1;self.rel={'id':1,'tag_name':tag,'body':body,'draft':True,'assets':[]};return self.rel
 def by_id(self,rid):return self.rel
 def upload(self,tag,path):
  self.uploads.append(path.name);self.rel['assets'].append({'name':path.name,'size':path.stat().st_size,'digest':'sha256:'+sha(path.read_bytes()),'state':'uploaded'})
 def publish(self,rid):self.published+=1;self.rel['draft']=False
 def download(self,tag,name,directory): (pathlib.Path(directory)/name).write_bytes(self.zipbytes)
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.t=pathlib.Path(self.temp.name);self.z=self.t/'terra.zip';self.s=self.t/'SHA256SUMS.txt';self.game=b'game';self.credits=b'credits';
  with zipfile.ZipFile(self.z,'w') as z:z.writestr('terra.html',self.game);z.writestr('credits.html',self.credits);z.writestr('README.txt',README)
  self.s.write_text('fixture');self.files=[self.z,self.s];self.f=Fake()
 def tearDown(self):self.temp.cleanup()
 def go(self):return deliver(self.f,S,TAG,self.files,self.game,self.credits)
 def test_happy(self):self.assertEqual(self.go(),'published');self.assertEqual(self.f.published,1);self.assertEqual(len(self.f.uploads),2)
 def test_resume_partial(self):
  self.f.create_draft(TAG,S,BODY);self.f.ref=S;self.f.upload(TAG,self.z);self.f.uploads=[];self.assertEqual(self.go(),'published');self.assertEqual(self.f.uploads,['SHA256SUMS.txt'])
 def test_mismatch(self):
  self.f.create_draft(TAG,S,BODY);self.f.ref=S;self.f.rel['assets']=[{'name':'terra.zip','size':1,'digest':'sha256:'+'0'*64,'state':'uploaded'}]
  with self.assertRaises(ValueError):self.go()
  self.assertEqual(self.f.published,0)
 def test_stale_and_tag_race(self):
  self.f.main='b'*40
  with self.assertRaises(ValueError):self.go()
  self.f.main=S;self.f.race=True
  with self.assertRaises(ValueError):self.go()
  self.assertEqual(self.f.published,0)
 def test_existing_tag_refused(self):
  self.f.ref='b'*40
  with self.assertRaises(ValueError):self.go()
  self.assertEqual(self.f.created,0)
 def test_latest_noop(self):
  self.f.zipbytes=self.z.read_bytes();self.f.previous={'tag_name':'old','assets':[{'name':'terra.zip','size':len(self.f.zipbytes),'digest':'sha256:'+sha(self.f.zipbytes),'state':'uploaded'}]}
  self.assertEqual(self.go(),'already published');self.assertEqual(self.f.created,0)
 def test_legacy_not_equal(self):
  with zipfile.ZipFile(self.z,'w') as z:z.writestr('terra.html',self.game)
  self.f.zipbytes=self.z.read_bytes();self.f.previous={'tag_name':'old','assets':[{'name':'terra.zip','size':len(self.f.zipbytes),'digest':'sha256:'+sha(self.f.zipbytes),'state':'uploaded'}]}
  self.assertEqual(self.go(),'published')
if __name__=='__main__':unittest.main()
