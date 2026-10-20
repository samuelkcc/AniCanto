import sys,json,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import license_inventory

class LicenseInventoryTests(unittest.TestCase):
 def test_merge_runtime_duplicates_preserves_distinct_notices_and_origins(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'Licenses').mkdir()
   for name,text in [('one','Copyright A'),('two','Copyright A'),('three','Copyright B')]:
    dist=root/'runtimes'/name/'lib/python3.11/site-packages/example-1.dist-info';dist.mkdir(parents=True)
    (dist/'METADATA').write_text('Name: example\nVersion: 1\nLicense-Expression: MIT\n');(dist/'LICENSE').write_text(text)
   records=license_inventory.generate(root)
   self.assertEqual(len(records),1);self.assertEqual(set(records[0]['origins']),{'one','two','three'})
   self.assertEqual(len(records[0]['files']),2)
   self.assertEqual(sum(map(len,records[0]['noticeSources'].values())),3)
 def test_core_not_duplicated_as_aggregate_and_versions_not_merged(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'runtimes').mkdir();(root/'Licenses/anicanto-core').mkdir(parents=True)
   (root/'Licenses/anicanto-core/LICENSE').write_text('notice')
   (root/'core-dependencies.json').write_text(json.dumps([dict(name='crate',version=v,license='MIT',origin='Rust',files=['Licenses/anicanto-core/LICENSE']) for v in ['1','2']]))
   rows=license_inventory.generate(root)
   self.assertEqual([r['version'] for r in rows],['1','2']);self.assertFalse(any(r['name']=='anicanto-core' for r in rows))
