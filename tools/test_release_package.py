import pathlib,tempfile,unittest,zipfile
import release_package as p
C='game-icons.net creativecommons.org/licenses/by/3.0/ перекраш delapouite guard13007 lorc sbed skoll zeromancer atomicrealm.itch.io'
class Test(unittest.TestCase):
 def test_context(self):
  sha='a'*40;e={'workflow_run':{'conclusion':'success','head_branch':'main','head_sha':sha}}
  p.validate_context(e,sha,'build-20261028-0030')
  for bad in ('../x','build-20261028-0030-x'):
   with self.assertRaises(ValueError):p.validate_context(e,sha,bad)
  with self.assertRaises(ValueError):p.validate_context(e,'b'*40,'build-20261028-0030')
  e['workflow_run']['conclusion']='failure'
  with self.assertRaises(ValueError):p.validate_context(e,sha,'build-20261028-0030')
 def test_package(self):
  with tempfile.TemporaryDirectory() as d:
   t=pathlib.Path(d);(t/'play').mkdir();(t/'play/index.html').write_text('game');(t/'credits.html').write_text(C);(t/'secret.txt').write_text('private')
   z=t/'x.zip';a=p.package(t,z);z2=t/'z.zip';self.assertEqual(a,p.package(t,z2));self.assertEqual(z.read_bytes(),z2.read_bytes())
   with zipfile.ZipFile(z) as f:self.assertEqual(f.namelist(),['terra.html','credits.html','README.txt']);self.assertEqual(f.read('terra.html'),b'game')
   with self.assertRaises(ValueError):p.package(t,z)
   with self.assertRaises(ValueError):p.verify_archive(z,{'terra.html':b'altered','credits.html':C.encode(),'README.txt':p.README})
   (t/'play/index.html').unlink();(t/'play/index.html').symlink_to(t/'secret.txt')
   with self.assertRaises(ValueError):p.package(t,t/'y.zip')
   (t/'play/index.html').unlink();(t/'play').rmdir();(t/'play').symlink_to(t,target_is_directory=True)
   with self.assertRaises(ValueError):p.package(t,t/'q.zip')
 def test_identity_and_resume_plan(self):
  a={'terra.html':'a'*64,'credits.html':'b'*64,'README.txt':'c'*64};self.assertTrue(p.compare_latest(a,a));self.assertFalse(p.compare_latest({'terra.html':'a'*64},a));self.assertFalse(p.compare_latest(dict(a,**{'credits.html':'d'*64}),a))
  self.assertEqual(p.draft_plan('a'*40,'a'*40,{'terra.zip':'b'*64},{'terra.zip':'b'*64,'SHA256SUMS.txt':'c'*64}),['SHA256SUMS.txt'])
  with self.assertRaises(ValueError):p.draft_plan('d'*40,'a'*40,{},a)
  with self.assertRaises(ValueError):p.draft_plan('a'*40,'a'*40,{'terra.zip':'d'*64},{'terra.zip':'b'*64})
if __name__=='__main__':unittest.main()
