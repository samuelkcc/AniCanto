import hashlib,json,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];RES=ROOT/'Resources'

class OriginalAssistantAssets(unittest.TestCase):
 def test_every_theme_has_four_full_cast_covers_and_only_female_active_identities(self):
  cast=json.loads((RES/'assistant-characters.json').read_text())['characters']
  self.assertEqual(len(cast),9);ids={c['id'] for c in cast}
  self.assertTrue(all(c['gender']=='female' for c in cast))
  self.assertEqual([c['theme'] for c in cast if c['retainedOriginal']],['studio'])
  images=json.loads((RES/'welcome-art/provenance.json').read_text())['covers']
  self.assertEqual(len(images),36)
  self.assertEqual({r['theme'] for r in images},{c['theme'] for c in cast})
  self.assertEqual(len({c['artStyle'] for c in cast}),9)
  for theme in {r['theme'] for r in images}:
   self.assertEqual({r['variant'] for r in images if r['theme']==theme},{1,2,3,4})
  self.assertEqual({r['file'] for r in images},{p.name for p in (RES/'welcome-art').glob('welcome-*.png')})
  for row in images:
   character=next(c for c in cast if c['theme']==row['theme'])
   self.assertEqual(character['canonicalCoverTheme'],row['theme'])
   self.assertIn(dict(file=row['file'],sha256=row['sha256']),character['canonicalCovers'])
   path=RES/'welcome-art'/row['file'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),row['sha256'])
   with Image.open(path) as im:
    self.assertIn('A',im.getbands());alpha=im.getchannel('A');self.assertEqual(alpha.getextrema(),(0,255))
    box=alpha.point(lambda a:255 if a>=32 else 0).getbbox()
    self.assertGreater(min(box[0],box[1],im.width-box[2],im.height-box[3]),5,'Cover is cut at its outer edge')
 def test_working_pose_and_walking_row_use_current_atlas_without_clipping(self):
  rigs=json.loads((RES/'assistant-rigs.json').read_text())
  self.assertEqual(len(rigs),9)
  for key,rig in rigs.items():
   path=RES/rig['image'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),rig['sha256'])
   self.assertEqual(rig['gender'],'female');self.assertEqual(rig['characterId'],'assistant-'+key)
   character=next(c for c in json.loads((RES/'assistant-characters.json').read_text())['characters'] if c['theme']==key)
   self.assertEqual(rig['sha256'],character['sha256']);self.assertEqual(rig['artStyle'],character['artStyle'])
   with Image.open(path) as im:
    self.assertEqual(list(im.size),rig['imageSize']);x,y,w,h=rig['rect']
    self.assertTrue(0<x<x+w<im.width and 0<y<y+h<rig['rowCuts'][1])
    self.assertTrue(0<rig['rowCuts'][1]<rig['rowCuts'][2]<im.height)
    box=im.crop((x,y,x+w,y+h)).getchannel('A').point(lambda a:255 if a>=32 else 0).getbbox()
    self.assertGreater(min(box[0],box[1],w-box[2],h-box[3]),0)

 def test_round_cartoon_uses_its_own_proportions(self):
  rig=json.loads((RES/'assistant-rigs.json').read_text())['future']
  self.assertEqual(rig['artStyle'],'round-three-head-cartoon')
  self.assertGreater(rig['skin']['neckY'],.35)
  self.assertGreater(rig['rect'][2]/rig['rect'][3],.55)

if __name__=='__main__':unittest.main()
