import json
from pathlib import Path
from collections import Counter, defaultdict
base=Path(r'C:\Dev\AIpinho\reports\sprint21_evidence')
summary={}
for name in ['approvals_pending','config_permission_matrix','policy_capabilities','chat_model_status','config_workspaces','config_providers','config_agents','policy_actions','policy_approvals']:
    path=base/f'{name}.json'
    try:
        data=json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception as e:
        summary[name]={'error':str(e)}
        continue
    if name=='approvals_pending':
        approvals=data.get('approvals') if isinstance(data,dict) else data
        if not isinstance(approvals,list): approvals=[]
        by_status=Counter(a.get('status') for a in approvals)
        by_session=Counter(a.get('session_id') or '<none>' for a in approvals)
        by_operation=Counter(a.get('operation_type') or '<none>' for a in approvals)
        by_execution=Counter(a.get('execution_status') or '<none>' for a in approvals)
        dangling=[a for a in approvals if not a.get('run_id') and not a.get('task_id')]
        temp_paths=[p for a in approvals for p in (a.get('target_paths') or []) if isinstance(p,str) and ('pytest-' in p or 'Temp' in p)]
        summary[name]={
          'count':len(approvals), 'by_status':dict(by_status), 'by_session_top':by_session.most_common(8),
          'by_operation':dict(by_operation), 'by_execution':dict(by_execution), 'dangling_without_run_task':len(dangling),
          'target_paths_with_temp_or_pytest':len(temp_paths),
          'sample_ids':[a.get('approval_id') for a in approvals[:8]]
        }
    elif name=='config_workspaces':
        items=data.get('workspaces') or data.get('items') or data if isinstance(data,list) else []
        if isinstance(items,dict): items=list(items.values())
        roles=Counter((w.get('role') if isinstance(w,dict) else None) for w in items)
        summary[name]={'count':len(items), 'roles':dict(roles), 'sample':[w for w in items[:5] if isinstance(w,dict)]}
    elif name=='policy_actions':
        actions=data.get('actions') if isinstance(data,dict) else data
        if isinstance(actions,dict): keys=list(actions.keys())
        elif isinstance(actions,list): keys=[a.get('action_id') or a.get('id') or a.get('name') for a in actions if isinstance(a,dict)]
        else: keys=[]
        summary[name]={'count':len(keys), 'actions':keys[:80]}
    elif name=='policy_capabilities':
        caps=data.get('capabilities') if isinstance(data,dict) else data
        if isinstance(caps,dict): keys=list(caps.keys())
        elif isinstance(caps,list): keys=[c.get('capability_id') or c.get('id') or c.get('name') for c in caps if isinstance(c,dict)]
        else: keys=[]
        summary[name]={'count':len(keys), 'capabilities':keys[:80], 'raw_keys':list(data.keys()) if isinstance(data,dict) else []}
    else:
        if isinstance(data,dict):
            summary[name]={'keys':list(data.keys()), 'status':data.get('status'), 'excerpt':{k:data[k] for k in list(data.keys())[:8]}}
        else:
            summary[name]={'type':type(data).__name__, 'count':len(data) if hasattr(data,'__len__') else None}
(base/'structured_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2)[:12000])
