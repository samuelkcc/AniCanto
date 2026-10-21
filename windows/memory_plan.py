"""Explain Windows model memory without conflating system RAM and dedicated VRAM.

Models run in stages, so each pool displays its largest single-model estimate.
Ollama may use a CPU/GPU split at runtime; the planner requires a full GPU fit
before offering a GPU profile, then setup verifies the actual adapter.
"""

def pools(plan):
    hardware=plan.get('hardware') or {}
    ram=float(hardware.get('memoryGB') or 0)
    dedicated=hardware.get('backend') in ('cuda','rocm') and float(hardware.get('acceleratorMemoryGB') or 0)>0
    vram=float(hardware.get('acceleratorMemoryGB') or 0) if dedicated else 0.0
    reserve=float(plan.get('systemReserveGB') or max(8.,ram*.15))
    rows={row['id']:row for row in plan.get('downloads',[]) if row.get('id')}
    system=[];gpu=[]
    for role,ident in (plan.get('roles') or {}).items():
        row=rows.get(ident)
        if not row:continue
        need=float(row.get('estimatedMemoryGB') or 0)
        if need<=0:continue
        entry=dict(role=role,id=ident,gb=need)
        (system if role=='voice' and plan.get('voiceBackend')=='cpu' or not dedicated else gpu).append(entry)
    return dict(system=dict(capacity=ram,budget=max(0.,ram-reserve),peak=max((r['gb'] for r in system),default=0.),models=system),
                gpu=dict(capacity=vram,budget=min(max(0.,ram-reserve),vram*.8) if dedicated else 0.,peak=max((r['gb'] for r in gpu),default=0.),models=gpu),
                dedicated=dedicated,backend=hardware.get('backend','cpu'),reserve=reserve)

def fit_model(row,hardware):
    if row.get('retired') or row.get('licenseReviewRequired'):return False,'unavailable'
    ram=float(hardware.get('memoryGB') or 0);system=max(0.,ram-max(8.,ram*.15))
    backend=hardware.get('backend','cpu');vram=float(hardware.get('acceleratorMemoryGB') or 0)
    need=float(row.get('estimatedMemoryGB') or 0)
    if need<=0:return False,'unknown-memory'
    if row.get('engine')=='cosyvoice3' and backend!='cuda':return False,'requires-nvidia'
    if row.get('id')=='drama3-native-q2':return need<=system,'system'
    if backend in ('cuda','rocm'):return need<=min(system,vram*.8),'gpu'
    return need<=system,'system'
