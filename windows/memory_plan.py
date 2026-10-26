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
        memory=plan.get('voiceMemory') or {}
        if role=='voice' and ident=='drama3-native-q2':
            system.append(dict(role=role,id=ident,gb=float(memory.get('systemGB') or need)))
            if dedicated and plan.get('voiceBackend')=='cuda':
                gpu.append(dict(role=role,id=ident,gb=float(memory.get('gpuGB') or 0)))
        else:
            entry=dict(role=role,id=ident,gb=need)
            (system if role=='voice' and plan.get('voiceBackend')=='cpu' or not dedicated else gpu).append(entry)
    from compute_policy import budgets
    current=budgets(ram,vram,hardware.get('acceleratorFreeMemoryGB'),dedicated)
    return dict(system=dict(capacity=ram,budget=max(0.,ram-reserve),peak=max((r['gb'] for r in system),default=0.),models=system),
                gpu=dict(capacity=vram,budget=min(max(0.,ram-reserve),current['acceleratorBudgetGB']) if dedicated else 0.,peak=max((r['gb'] for r in gpu),default=0.),models=gpu),
                dedicated=dedicated,backend=hardware.get('backend','cpu'),reserve=reserve)

def fit_model(row,hardware):
    if row.get('retired') or row.get('licenseReviewRequired'):return False,'unavailable'
    ram=float(hardware.get('memoryGB') or 0);system=max(0.,ram-max(8.,ram*.15))
    backend=hardware.get('backend','cpu');vram=float(hardware.get('acceleratorMemoryGB') or 0)
    need=float(row.get('estimatedMemoryGB') or 0)
    if need<=0:return False,'unknown-memory'
    if row.get('engine')=='cosyvoice3' and backend!='cuda':return False,'requires-nvidia'
    if row.get('id')=='drama3-native-q2':return need<=system,'system'
    if backend in ('cuda','rocm'):
        from compute_policy import budgets
        available=budgets(ram,vram,hardware.get('acceleratorFreeMemoryGB'),True)['acceleratorBudgetGB']
        return need<=min(system,available),'gpu'
    return need<=system,'system'

def can_attempt_over_budget(row,hardware):
    """A deliberate model choice may use headroom or swap; never claim it fits."""
    fits,pool=fit_model(row,hardware)
    if fits or pool not in ('system','gpu'):return False
    ram=float(hardware.get('memoryGB') or 0)
    vram=float(hardware.get('acceleratorMemoryGB') or 0)
    capacity=ram if pool=='system' else min(ram,vram)
    return capacity>0 and float(row.get('estimatedMemoryGB') or 0)<=capacity
