import unittest
from pages_probe import ready
class Probe(unittest.TestCase):
 def test_exact_deployment(self):
  s='a'*40;good={'name':'pages build and deployment','event':'dynamic','head_branch':'main','head_sha':s,'status':'completed','conclusion':'success'}
  self.assertEqual(ready([good],s),good)
  for changes in ({'head_sha':'b'*40},{'head_branch':'other'},{'event':'push'},{'conclusion':'failure'},{'status':'in_progress'},{'name':'other'}):
   self.assertIsNone(ready([good|changes],s))
if __name__=='__main__':unittest.main()
