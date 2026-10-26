"""Frontend actions must traverse the real native allowlist, not only Python."""
from pathlib import Path
import re,unittest
ROOT=Path(__file__).resolve().parents[1]
class OperationContractTests(unittest.TestCase):
 def operations(self):
  source=(ROOT/'studio/src-tauri/src/main.rs').read_text()
  return set(re.findall(r'"([\w-]+)"',source.split('const DESKTOP_OPERATIONS:')[1].split(';')[0]))
 def test_all_literal_frontend_rpc_operations_are_allowed_by_native_host(self):
  calls=set()
  for path in (ROOT/'studio/web').rglob('*.js'):calls.update(re.findall(r"\brpc\(['\"]([\w-]+)['\"]",path.read_text()))
  self.assertTrue(calls);self.assertEqual(calls-self.operations(),set())
 def test_subtitle_and_triage_actions_are_allowed_without_opening_internal_task_endpoints(self):
  allowed=self.operations();self.assertTrue({'set-external-subtitle','review-triage'}<=allowed)
  self.assertTrue({'execute-shell','start','setup','render','finish','speech-studio'}.isdisjoint(allowed))
if __name__=='__main__':unittest.main()
