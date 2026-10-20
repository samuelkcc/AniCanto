"""Public binaries may retain required attributions but never builder home paths."""
import hashlib,json,struct,sys,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import build_environment,sanitize_build_paths as native
class BuildPrivacyTests(unittest.TestCase):
 def fixture(self,prefix,code=False,filename='file.cpp'):
  raw=bytearray(0x500);raw[:2]=b'MZ';struct.pack_into('<I',raw,0x3c,0x80);raw[0x80:0x84]=b'PE\0\0';struct.pack_into('<HH',raw,0x84,0x8664,2);struct.pack_into('<H',raw,0x94,0xf0)
  start=0x80+24+0xf0
  for i,(name,offset,flags) in enumerate([(b'.text',0x300,0x60000020),(b'.rdata',0x400,0x40000040)]):
   p=start+40*i;raw[p:p+len(name)]=name;struct.pack_into('<II',raw,p+16,0x100,offset);struct.pack_into('<I',raw,p+36,flags)
  data=prefix+filename.encode();at=0x310 if code else 0x410;raw[at:at+len(data)]=data;return bytes(raw)
 def test_only_source_filename_literals_change_with_code_and_length_preserved(self):
  prefix=b'/'+b'Users/'+b'private-builder/';raw=self.fixture(prefix);clean,evidence=native.remap(raw,prefix)
  self.assertEqual(len(clean),len(raw));self.assertEqual(native.code_hashes(raw),native.code_hashes(clean));self.assertNotIn(prefix,clean);self.assertEqual(evidence['replacedSourceLocations'],1)
 def test_utf16_source_locations_are_also_normalised(self):
  prefix=b'/'+b'Users/'+b'private-builder/';raw=bytearray(self.fixture(prefix));raw[0x410:0x500]=b'\0'*0xf0;name=(prefix.decode()+'file.cpp').encode('utf-16-le');raw[0x410:0x410+len(name)]=name;clean,evidence=native.remap(bytes(raw),prefix)
  self.assertNotIn(prefix.decode().encode('utf-16-le'),clean);self.assertEqual(native.code_hashes(raw),native.code_hashes(clean));self.assertEqual(evidence['changes'][0]['encoding'],'utf-16-le')
 def test_code_sections_and_runtime_paths_are_never_patched(self):
  prefix=b'/'+b'Users/'+b'private-builder/'
  with self.assertRaisesRegex(ValueError,'outside'):native.remap(self.fixture(prefix,code=True),prefix)
  with self.assertRaisesRegex(ValueError,'diagnostic'):native.remap(self.fixture(prefix,filename='models/weights.bin'),prefix)
 def test_repeat_preparation_without_native_inputs_preserves_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);e=root/'licenses/build-path-remapping.json';e.parent.mkdir();e.write_text(json.dumps(dict(files=[])));before=e.stat().st_mtime_ns
   with patch.object(native,'ROOT',root):
    self.assertEqual(native.prepare()['files'],[]);self.assertEqual(native.prepare()['files'],[])
   self.assertEqual(e.stat().st_mtime_ns,before)
 def test_rust_flags_preserve_existing_arguments_and_anonymise_spaced_prefix(self):
  env=build_environment.rust_environment('x86_64-pc-windows-msvc',base={'RUSTFLAGS':'-C opt-level=s'},home='/private builder')
  self.assertNotIn('RUSTFLAGS',env);flags=env['CARGO_ENCODED_RUSTFLAGS'].split('\x1f');self.assertIn('opt-level=s',flags);self.assertIn('target-feature=+crt-static',flags);self.assertIn('--remap-path-prefix=/private builder=/build-home',flags)
 def test_host_refreshes_versioned_interface_before_native_embedding(self):
  import build_shared_host
  order=[]
  with patch('prepare_shared_studio.prepare',side_effect=lambda:order.append('prepare')),patch.object(build_shared_host.subprocess,'run',side_effect=lambda *a,**k:order.append('compile')):
   build_shared_host.build()
  self.assertEqual(order,['prepare','compile'])
if __name__=='__main__':unittest.main()
