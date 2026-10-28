import hashlib, pathlib, tempfile, unittest, zipfile
import release_package as p
class Test(unittest.TestCase):
 def test_context(self):
  sha='a'*40;e={'workflow_run':{'conclusion':'success','head_branch':'main','head_sha':sha}}
  p.validate_context(e,sha,'build-20261028-0030')
  for bad in ('../x','build-20261028-0030-x'):
   with self.assertRaises(ValueError):p.validate_context(e,sha,bad)
  with self.assertRaises(ValueError):p.validate_context(e,'b'*40,'build-20261028-0030')
  e['workflow_run']['conclusion']='failure'
  with self.assertRaises(ValueError):p.validate_context(e,sha,'build-20261028-0030')
 def test_dedup(self):
  self.assertTrue(p.is_duplicate('a'*64,['a'*64]))
  self.assertFalse(p.is_duplicate('a'*64,['b'*64]))
  with self.assertRaises(ValueError): p.is_duplicate('a'*64,['unknown'])
 def test_package(self):
  with tempfile.TemporaryDirectory() as d:
   t=pathlib.Path(d);(t/'play').mkdir();(t/'play/index.html').write_text('game');(t/'credits.html').write_text('CC BY')
   (t/'secret.txt').write_text('private');z=t/'x.zip';p.package(t,z)
   with zipfile.ZipFile(z) as f:self.assertEqual(f.namelist(),['terra.html','credits.html','README.txt']);self.assertEqual(f.read('terra.html'),b'game')
   with self.assertRaises(ValueError):p.package(t,z)
   with self.assertRaises(ValueError):p.verify_archive(z,{'terra.html':b'altered','credits.html':b'CC BY','README.txt':b''})
   (t/'play/index.html').unlink();(t/'play/index.html').symlink_to(t/'secret.txt')
   with self.assertRaises(ValueError):p.package(t,t/'y.zip')
if __name__=='__main__':unittest.main()
