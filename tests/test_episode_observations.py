import copy,json,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).parents[1]/'Resources'))
import character_observations as observations
import appearance_reconcile as appearance
import reference_quality as quality


class EpisodeObservations(unittest.TestCase):
    def person(self,ident='v1',left=.1):
        head=[left,.1,left+.3,.8];mouth=[left+.05,.5,left+.25,.6]
        return dict(visualId=ident,headVisible=True,characterBox=head,frameBoxes=[head]*4,
                    mouthBoxes=[mouth]*4,speaking=True,mouthChanged=True,confidence=.99)

    def image(self,path,people,mode='mouth'):
        sheet=Image.new('RGB',(1024,170),'grey');draw=ImageDraw.Draw(sheet)
        for n in range(4):
            if mode=='global':draw.rectangle((256*n,24,256*(n+1)-1,167),fill='white' if n%2 else 'black')
            else:
                for p in people:
                    a,b,c,d=p['mouthBoxes'][n]
                    draw.rectangle((256*n+a*256,24+b*144,256*n+c*256,24+d*144),fill='black' if mode=='static' or n%2 else 'white')
        sheet.save(path)

    def test_inventory_covers_late_short_and_mixed_dialogue(self):
        cues=[dict(start=i*2,end=i*2+1,enabled=True,mixedVoices=True) for i in range(300)]
        cues.append(dict(start=0,end=.1));cues.append(dict(start=0,end=2,enabled=False))
        self.assertEqual(observations.eligible_indices(cues),list(range(300)))

    def test_grounding_inputs_are_individual_frames_with_explicit_image_order(self):
        from visual_identity import inference_images
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);board=root/'board.jpg'
            sheet=Image.new('RGB',(1024,170),'black')
            colors=['red','green','blue','white']
            for n,color in enumerate(colors):sheet.paste(Image.new('RGB',(256,144),color),(256*n,24))
            sheet.save(board)
            photo=root/'head.jpg';Image.new('RGB',(80,80),'purple').save(photo)
            images,mapping=inference_images([dict(visualId='v1',photos=[str(photo)])],{7:board},[7],root/'debug.jpg')
            self.assertEqual(len(images),5);self.assertIn('ROW index=7',mapping);self.assertIn('ONLY to IMAGE 4',mapping)
            for n,path in enumerate(images[1:]):
                with Image.open(path) as image:
                    self.assertEqual(image.size,(256,144))
                    rgb=np.asarray(image)[8:-8,8:-8];self.assertLess(float(np.std(rgb[:,:,0])),2)
            with Image.open(images[3]) as blue:self.assertGreater(blue.getpixel((128,72))[2],240)

    def test_multicharacter_boxes_are_independent_and_duplicate_boxes_rejected(self):
        a=self.person();b=self.person('v2',.6)
        self.assertEqual(len(observations.validate_people(dict(characters=[a,b,a]),{'v1','v2'})),2)
        b['characterBox']=a['characterBox']
        self.assertEqual(len(observations.validate_people(dict(characters=[a,b]),{'v1','v2'})),1)

    def test_new_appearance_ids_cannot_be_unknown_or_duplicate_existing_ids(self):
        from visual_speakers import observation_schema
        schema,new=observation_schema([5,6],[dict(id='v4',appearance='A distinctive purple hooded character')])
        self.assertEqual(new[0],'v5')
        self.assertNotIn('unknown',schema['properties']['roster']['items']['properties']['id']['enum'])
        self.assertNotIn('v4',new)
        self.assertIn('v4',schema['properties']['rows']['items']['properties']['characters']['items']['properties']['visualId']['enum'])

    def test_moderate_appearance_evidence_is_retained_without_speaker_authority(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'image.jpg';person=self.person();person['confidence']=.9;self.image(p,[person])
            row=dict(index=0,visualId='unknown',characters=observations.validate_people(dict(characters=[person]),{'v1'}),continuousShot=True,multipleSpeakers=False)
            observations.apply_temporal_checks([row],{0:p})
            self.assertEqual(row['visibleCharacterIds'],['v1'])
            self.assertEqual(row['activeCharacterIds'],[])
            self.assertFalse(row['speaking'])

    def test_hand_only_description_cannot_seed_a_new_identity(self):
        from visual_speakers import validated_batch
        row=dict(index=1,visualId='v1',speaking=False,mouthChanged=False,continuousShot=True,multipleSpeakers=False,headVisible=False,characterBox=[],confidence=.9,characters=[])
        rows,roster,_=validated_batch(dict(rows=[row],roster=[dict(id='v1',appearance='pale hand with short nails and a yellow sleeve')]),[1],[])
        self.assertEqual(roster,[]);self.assertEqual(rows[0]['visualId'],'unknown')

    def test_portrait_quality_rejections_are_cached_and_never_enter_memory(self):
        from portrait_validation import validate
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);photos=[]
            for n in range(2):
                path=root/f'{n}.jpg';Image.new('RGB',(80,80),'red' if n else 'blue').save(path)
                photos.append(dict(avatar=str(path),sourceFrame=str(path),time=n,index=n,visualId='v1'))
            gallery=[dict(visualId='v1',photos=[p['avatar'] for p in photos],observations=photos)]
            calls=[]
            def inspect(image,requests):
                calls.append(requests)
                return dict(crops=[dict(index=r['index'],usableHead=True,singleHead=r['index']==1,matchesAppearance=True,confidence=.95) for r in requests])
            roster=[dict(id='v1',appearance='distinctive red hair and black jacket')]
            for _ in range(2):
                passed=validate(gallery,roster,root,inspect,'test')
                self.assertEqual(passed[0]['photos'],[photos[1]['avatar']])
            self.assertEqual(len(calls),1)
            self.assertEqual(json.loads((root/'visual-photo-atlas.json').read_text())['gallery'][0]['photos'],[photos[1]['avatar']])

    def test_portrait_checks_stop_after_eight_failed_candidates_per_identity(self):
        from portrait_validation import validate
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);photos=[]
            for n in range(12):
                path=root/f'{n}.jpg';Image.new('RGB',(80,80),(n*20,0,0)).save(path)
                photos.append(dict(avatar=str(path),sourceFrame=str(path),time=n,index=n,visualId='v1'))
            gallery=[dict(visualId='v1',photos=[p['avatar'] for p in photos],observations=photos)];calls=[]
            def fail(image,requests):calls.extend(requests);raise ValueError('unknown head')
            for _ in range(2):self.assertEqual(validate(gallery,[dict(id='v1',appearance='red helmet with white marking')],root,fail,'test'),[])
            self.assertEqual(len(calls),8)

    def test_static_or_camera_motion_cannot_prove_speaking(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'image.jpg';person=self.person()
            for mode in ('static','global'):
                self.image(p,[person],mode)
                result=observations.temporal_evidence(p,person)
                self.assertNotEqual(result['status'],'supported')

    def test_localized_mouth_change_is_supported_but_not_certified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'image.jpg';person=self.person();self.image(p,[person])
            result=observations.temporal_evidence(p,person)
            self.assertEqual(result['status'],'supported');self.assertFalse(result['certified'])

    def test_visible_reaction_head_does_not_overwrite_offscreen_speaker(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'image.jpg';person=self.person();self.image(p,[person],'static')
            row=dict(index=0,visualId='unknown',characters=[person],continuousShot=True,multipleSpeakers=False)
            observations.apply_temporal_checks([row],{0:p})
            self.assertFalse(row['speaking']);self.assertEqual(row['visualId'],'v1')
            self.assertTrue(row['headVisible'])

    def test_two_moving_mouths_remain_multiple_without_arbitrary_speaker(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'image.jpg';people=[self.person(),self.person('v2',.6)];self.image(p,people)
            row=dict(index=0,visualId='unknown',characters=people,continuousShot=True,multipleSpeakers=False)
            observations.apply_temporal_checks([row],{0:p})
            self.assertTrue(row['multipleSpeakers']);self.assertFalse(row['speaking']);self.assertEqual(row['visualId'],'unknown')

    def test_mouth_box_outside_head_and_missing_tracking_are_unavailable(self):
        person=self.person();person['mouthBoxes'][0]=[.7,.7,.9,.8]
        self.assertEqual(observations.temporal_evidence('unused',person)['status'],'unavailable')
        person['mouthBoxes']=[];self.assertEqual(observations.temporal_evidence('unused',person)['status'],'unavailable')

    def gallery(self,root,ids):
        result=[]
        for ident in ids:
            p=root/(ident+'.jpg');Image.new('RGB',(80,80),'red').save(p)
            result.append(dict(visualId=ident,photos=[str(p)]))
        return result

    def test_co_visible_heads_cannot_merge_even_matching_photographs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);gallery=self.gallery(root,['v1','v2']);calls=[]
            rows=[dict(index=0,visualId='v1',characters=[self.person(),self.person('v2',.6)])]
            appearance.consolidate({'key':'test'},root,[],rows,[],gallery,lambda *a:calls.append(a))
            self.assertEqual(calls,[]);self.assertEqual(json.loads((root/'visual-appearance-links.json').read_text())['aliases'],{'v1':'v1','v2':'v2'})

    def test_complete_gallery_links_are_saved_and_resume_does_not_repeat_llm(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);gallery=self.gallery(root,['v1','v2']);rows=[dict(index=0,visualId='v1'),dict(index=1,visualId='v2')];calls=[]
            def compare(path,pairs):
                calls.append(pairs);return {'pairs':[dict(left=a,right=b,sameAppearance=True,distinctiveAgreement=True,confidence=.99) for a,b in pairs]}
            result=appearance.consolidate({'key':'test'},root,[],copy.deepcopy(rows),[],gallery,compare)
            self.assertEqual(result[1]['visualId'],'v1')
            appearance.consolidate({'key':'test'},root,[],copy.deepcopy(rows),[],gallery,compare)
            self.assertEqual(len(calls),1)

    def test_failed_visual_reply_is_finite_and_preserves_two_identities(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);gallery=self.gallery(root,['v1','v2']);calls=[]
            def fail(*a):calls.append(1);raise ValueError('broken reply')
            for _ in range(2):appearance.consolidate({'key':'test'},root,[],[],[],gallery,fail)
            self.assertEqual(calls,[1]);self.assertEqual(json.loads((root/'visual-appearance-links.json').read_text())['aliases'],{'v1':'v1','v2':'v2'})

    def test_appearance_chain_cannot_merge_visually_contradictory_endpoints(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);gallery=self.gallery(root,['v1','v2','v3'])
            def compare(path,pairs):
                return {'pairs':[dict(left=a,right=b,sameAppearance=(a,b)!=('v1','v3'),distinctiveAgreement=True,confidence=.99) for a,b in pairs]}
            appearance.consolidate({'key':'chain'},root,[],[],[],gallery,compare)
            aliases=json.loads((root/'visual-appearance-links.json').read_text())['aliases']
            self.assertEqual(aliases['v1'],aliases['v2']);self.assertNotEqual(aliases['v1'],aliases['v3'])

    def test_background_residual_is_retained_after_reference_pcm_inspection(self):
        sr=24000;t=np.arange(sr*4)/sr
        music=.15*np.sin(2*np.pi*440*t);speech=.03*np.sin(2*np.pi*180*t)*(np.sin(2*np.pi*3*t)>0)
        evidence=quality.measure(music+speech,sr,music)
        self.assertIn('shared-background-residual',evidence['warnings'])
        without=quality.measure(music+speech,sr)
        after=quality.conditioned_quality(without,evidence)
        self.assertLess(after['score'],without['score']);self.assertIn('shared-background-residual',after['warnings'])

    def test_loud_different_background_alone_not_shared_residual(self):
        sr=24000;t=np.arange(sr*4)/sr
        result=quality.measure(.15*np.sin(2*np.pi*210*t),sr,.15*np.sin(2*np.pi*640*t))
        self.assertNotIn('shared-background-residual',result['warnings'])


if __name__=='__main__':unittest.main()
