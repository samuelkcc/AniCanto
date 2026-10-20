"""The release source check must reject corrupted inputs and mismatched binaries."""
import hashlib,io,json,sys,tarfile,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ffmpeg_source_audit as audit,public_source
class FFmpegSourceAuditTests(unittest.TestCase):
 def fixture(self,base):
  p=base/'source.tar.gz'
  with tarfile.open(p,'w:gz') as t:
   data=b'original source';i=tarfile.TarInfo('lib/source.c');i.size=len(data);t.addfile(i,io.BytesIO(data))
  z=base/'binary.zip'
  with zipfile.ZipFile(z,'w') as a:a.writestr('build/bin/ffmpeg.exe',b'MZ fixture v123 --enable-gpl\0')
  def row(path):return dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
  return dict(materials=[row(p)],binary=row(z),unresolved=[],version='v123',configuration='--enable-gpl')
 def test_checks_actual_source_and_binary_and_fails_on_corruption(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);m=self.fixture(b);r=audit.verify_windows(b,m);self.assertTrue(r['sourceInputsRetained']);self.assertFalse(r['legalApproval'])
   (b/'source.tar.gz').write_bytes(b'wrong archive')
   with self.assertRaisesRegex(ValueError,'checksum'):audit.verify_windows(b,m)
 def test_wrong_binary_revision_or_configuration_and_open_inputs_fail(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);m=self.fixture(b);m['version']='another-revision'
   with self.assertRaisesRegex(ValueError,'version'):audit.verify_windows(b,m)
   m['version']='v123';m['configuration']='--another-config'
   with self.assertRaisesRegex(ValueError,'configuration'):audit.verify_windows(b,m)
   m['unresolved']=['missing library']
   with self.assertRaisesRegex(ValueError,'incomplete'):audit.verify_windows(b,m)
 def test_known_source_subsets_exclude_unused_sdk_binaries(self):
  data=json.loads((ROOT/'licenses/ffmpeg/source-subsets.json').read_text());amf=next(r for r in data['subsets'] if 'AMF' in r['component'])
  self.assertTrue(any(r['path'].startswith('amf/public/include/') for r in amf['files']))
  self.assertFalse(any(r['path'].startswith('Thirdparty/') or r['path'].lower().endswith(('.dll','.exe','.pdb')) for r in amf['files']))
  self.assertTrue(any('license' in r['path'].lower() for r in amf['files']))
 def test_only_approved_synthetic_audio_can_enter_source_candidate(self):
  p=ROOT/'Resources/natural-voices/yue-mid.wav';rel=p.relative_to(ROOT).as_posix();self.assertTrue(public_source.selected(rel));self.assertFalse(public_source.findings(p.read_bytes(),rel))
  self.assertIn('synthetic-reference-hash-mismatch',public_source.findings(b'RIFFxxxxWAVEwrong',rel));self.assertFalse(public_source.selected('Resources/personal-recording.wav'))
  self.assertFalse(public_source.selected('licenses/tools/uv-dependencies/example/LICENSE'))
if __name__=='__main__':unittest.main()
