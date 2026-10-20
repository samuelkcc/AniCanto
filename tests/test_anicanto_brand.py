import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import release_notices

class AniCantoBrandTests(unittest.TestCase):
 def test_identity_and_storage_survive_display_rename(self):
  cfg=json.loads((ROOT/'studio/src-tauri/tauri.conf.json').read_text())
  self.assertEqual(cfg['productName'],'AniCanto');self.assertEqual(cfg['identifier'],'com.sckc.cantosync.studio')
  host=(ROOT/'studio/src-tauri/src/main.rs').read_text()
  self.assertIn('Application Support/SamCantoSync',host);self.assertIn('CantoSync-Windows',host)
  self.assertIn('CANTOSYNC_STUDIO_DATA',host)
 def test_active_grant_changes_and_upstream_notice_remains_verbatim(self):
  with tempfile.TemporaryDirectory() as d:
   dest=Path(d);(dest/'Licenses/vendor').mkdir(parents=True)
   notice=dest/'Licenses/vendor/LICENSE';notice.write_text('Copyright upstream author')
   for name in ('CantoSync-MIT.txt','CantoSync-GPL-3.0.txt'):(dest/'Licenses'/name).write_text('old grant')
   rows=release_notices.install(dest)
   self.assertEqual((dest/'Licenses/AniCanto-MIT.txt').read_bytes(),(ROOT/'LICENSE').read_bytes())
   self.assertFalse((dest/'Licenses/CantoSync-MIT.txt').exists());self.assertEqual(notice.read_text(),'Copyright upstream author')
   self.assertTrue(any(r['name']=='AniCanto original brand icon' for r in rows))
   self.assertTrue(all((dest/f).is_file() for row in rows for f in row['files']))
 def test_default_theme_and_brand_are_not_another_theme_alias(self):
  js=(ROOT/'studio/web/model.js').read_text();app=(ROOT/'studio/web/app.js').read_text()
  self.assertIn("THEMES={studio:",js);self.assertIn("themeKey='studio'",app)
  self.assertNotIn("ensemble:'#",js)
  self.assertIn('AniCanto</div>',app)

if __name__=='__main__':unittest.main()
