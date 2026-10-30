"""Separate verified installation identity from optional hardware recommendations."""
REQUIRED_ROLES=('text','voice','speech','referenceSpeech','asr')

def verified(record):
 return record.get('modelLoadPassed') is True and record.get('speechInferencePassed') is True

def same_selection(plan,record):
 return (verified(record) and plan.get('engine')==record.get('engine')
         and all(plan.get('roles',{}).get(k)==record.get('roles',{}).get(k) for k in REQUIRED_ROLES))

def keep_verified_visual(plan,record):
 # A change in free VRAM can add or remove this optional role. It does not
 # replace a successful deployment. Keep only the optional role it verified.
 if same_selection(plan,record):
  role=record.get('roles',{}).get('visual')
  if role is None or role==plan.get('roles',{}).get('text'):
   plan['roles']['visual']=role
   plan['roleAnalysisMode']='audiovisual' if role else 'audio'

def status(plan,record,invalidated=False,cuda_ready=True):
 reasons=[]
 if any(not r.get('installed') for r in plan.get('downloads',[])):reasons.append('missing-models')
 if any(not r.get('installed') for r in plan.get('tools',[])):reasons.append('missing-tools')
 if not verified(record):reasons.append('verification-required')
 elif not same_selection(plan,record):reasons.append('selection-changed')
 elif plan.get('engine')=='drama3' and record.get('voiceBackend')!=plan.get('voiceBackend'):reasons.append('backend-changed')
 if invalidated:reasons.append('setup-invalidated')
 if plan.get('tools') and not cuda_ready:reasons.append('cuda-verification-required')
 return dict(ready=not reasons,reasons=reasons,filesPresent=not any(x in reasons for x in ('missing-models','missing-tools')))
