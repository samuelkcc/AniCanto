"""Compile the actual Swift event decoder/projection: incomplete previews must survive IPC."""
import json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(sys.platform=='darwin' and shutil.which('swiftc'),'requires the Mac native compiler')
class NativeEventProjectionTests(unittest.TestCase):
 def test_preview_and_later_complete_keep_their_delivery_identity(self):
  source=(ROOT/'Sources/Engine.swift').read_text()
  decoder=source[source.index('struct WorkerEvent:'):source.index('struct ComponentProgress:')]
  stubs='\n'.join('struct '+name+':Codable {}' for name in ['ProductionJourney','AudioTrackProgress','DownloadTransfer','ComponentProgress'])
  main=r'''import Foundation
let data=FileHandle.standardInput.readDataToEndOfFile()
let event=try JSONDecoder().decode(WorkerEvent.self,from:data)
FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject:event.sharedStudioFields(),options:[.sortedKeys]))
'''
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);(folder/'Types.swift').write_text('import Foundation\n'+stubs+'\n'+decoder)
   (folder/'main.swift').write_text(main);binary=folder/'projection'
   subprocess.run(['swiftc',str(folder/'Types.swift'),str(ROOT/'Sources/SharedStudioEvent.swift'),str(folder/'main.swift'),'-o',str(binary)],check=True,capture_output=True)
   preview=dict(stage='完成',message='Preview',output='preview.mp4',deliveryKind='preview',artifactRole='labelled-preview',previewOutput='preview.mp4',missingDialogue=16,incompleteDialogue=20,partial=True,workCached=True,unknownPrivateField='must not forward')
   def project(event):return json.loads(subprocess.check_output([str(binary)],input=json.dumps(event).encode()))
   actual=project(preview)
   self.assertEqual(actual,{k:v for k,v in preview.items() if k!='unknownPrivateField'})
   complete=dict(stage='完成',message='Saved',output='final.mp4',deliveryKind='complete',artifactRole='published',partial=False)
   self.assertEqual(project(complete),complete)
if __name__=='__main__':unittest.main()
