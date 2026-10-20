import hashlib,json,sys,tempfile,unittest,zipfile,shutil
from pathlib import Path
from unittest.mock import patch,Mock
sys.path[:0]=[str(Path(__file__).parents[1]/'Resources'),str(Path(__file__).parents[1]/'windows')]
import text_data,runtime_licenses,native_licenses

class TextDataTests(unittest.TestCase):
 def fixture(self,root):
  base=root/'source';docs=base/'licenses';docs.mkdir(parents=True);(docs/'MIT.txt').write_text('Original notice')
  archive=root/'data.zip'
  with zipfile.ZipFile(archive,'w') as z:z.writestr('tagger/data.json','{"word":"tag"}')
  raw=b'{"word":"tag"}'
  row=dict(id='tagger',subdir='taggers',revision='pinned',url='https://example.invalid/pinned.zip',archiveSHA256=hashlib.sha256(archive.read_bytes()).hexdigest(),archiveBytes=archive.stat().st_size,files=[dict(path='data.json',sha256=hashlib.sha256(raw).hexdigest())],documents=[dict(path='licenses/MIT.txt',sha256=hashlib.sha256(b'Original notice').hexdigest())])
  def download(url,path,*args):path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(archive,path)
  return base,row,download
 def test_pinned_install_reuse_and_repair_preserve_notices_and_unrelated_data(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);base,row,fn=self.fixture(root);data=root/'owned';download=Mock(side_effect=fn)
   with patch('text_data.manifest',return_value=(base,dict(packages=[row]))):
    for _ in range(2):text_data.install_nltk(data,download)
    self.assertEqual(download.call_count,1)
    target=data/'models/nltk/taggers/tagger';self.assertEqual((target/'AniCanto-LICENSES/MIT.txt').read_text(),'Original notice')
    other=target.parent/'custom-user-data';other.write_text('keep')
    (target/'data.json').write_text('damaged');text_data.install_nltk(data,download)
    self.assertEqual(download.call_count,2);self.assertEqual(other.read_text(),'keep')
 def test_tampered_notice_fails_before_downloading(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);base,row,fn=self.fixture(root);(base/'licenses/MIT.txt').write_text('changed');download=Mock(side_effect=fn)
   with patch('text_data.manifest',return_value=(base,dict(packages=[row]))):
    with self.assertRaises(ValueError):text_data.install_nltk(root/'owned',download)
   download.assert_not_called()
 def test_unexpected_zip_member_is_rejected_and_existing_data_kept(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);base,row,fn=self.fixture(root)
   with zipfile.ZipFile(root/'data.zip','a') as z:z.writestr('../escape','bad')
   row['archiveSHA256']=hashlib.sha256((root/'data.zip').read_bytes()).hexdigest()
   existing=root/'owned/models/nltk/taggers/tagger';existing.mkdir(parents=True);(existing/'data.json').write_text('old')
   with patch('text_data.manifest',return_value=(base,dict(packages=[row]))):
    with self.assertRaises(ValueError):text_data.install_nltk(root/'owned',fn)
   self.assertEqual((existing/'data.json').read_text(),'old');self.assertFalse((root/'escape').exists())
 def test_dictionary_and_voice_notices_are_visible_for_both_runtime_layouts(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for site in [root/'gsv-runtime/lib/python3.11/site-packages',root/'runtimes/gpt/Lib/site-packages']:
    info=site/'pyopenjtalk_plus-0.4.1.post9.dist-info';info.mkdir(parents=True);(info/'METADATA').write_text('Name: pyopenjtalk-plus\nVersion: 0.4.1.post9\nLicense: MIT\n')
    for name in ['dictionary/COPYING','htsvoice/LICENSE_mei_normal.htsvoice']:
     path=site/'pyopenjtalk'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('Original upstream '+name)
   mac=runtime_licenses.update(root);win=native_licenses.inventory(root)
   self.assertEqual(len(mac[0]['files']),2);self.assertEqual(len(win[0]['notices']),2)
