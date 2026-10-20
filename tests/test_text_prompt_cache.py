import unittest,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
from text_prompt_cache import PrefixCache
class PrefixCacheTests(unittest.TestCase):
 def test_exact_prefix_and_working_copy_isolation(self):
  cache=PrefixCache(minimum=4);cache.tokens=[1,2,3,4];cache.cache=[{'state':[10]}]
  work,rest=cache.prepare(None,[1,2,3,4,5,6]);self.assertEqual(rest,[5,6]);self.assertEqual(cache.reused,4)
  work[0]['state'][0]=999;self.assertEqual(cache.cache[0]['state'],[10])
 def test_changed_token_never_reuses_recurrent_state(self):
  cache=PrefixCache(minimum=4);cache.tokens=[1,2,3,4];cache.cache=[{}];cache.previous=[1,2,3,4,9]
  work,rest=cache.prepare(None,[1,2,8,4,9]);self.assertIsNone(work);self.assertEqual(rest,[1,2,8,4,9]);self.assertEqual(cache.reused,0)
 def test_short_and_exact_input_leave_generation_token(self):
  cache=PrefixCache();self.assertEqual(cache.prepare(None,[1,2]),(None,[1,2]))
  cache.tokens=[1,2];cache.cache=[{}]
  self.assertEqual(cache.prepare(None,[1,2]),(None,[1,2]))
  cache.clear();self.assertIsNone(cache.cache);self.assertEqual(cache.previous,[])
