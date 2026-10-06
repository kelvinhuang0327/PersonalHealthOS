import sys
sys.path.insert(0, '/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/backend')
from app.orchestrator.db import OrchestratorDB
from app.orchestrator.problem_signal import detect_product_issues, get_recently_completed_signatures
from app.orchestrator.task_pool import _TASK_TEMPLATES, pick_next_category

db = OrchestratorDB('/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/runtime/agent_orchestrator/orchestrator.db')
recent = db.list_tasks(limit=50)
sigs = get_recently_completed_signatures(recent)
print(f'Signatures on 7-day cooldown: {len(sigs)}')
for sig, ts in list(sigs.items())[:4]:
    print(f'  {sig[:50]}: {ts.date()}')

pool_sig_to_cat = {tmpl['duplicate_signature']: cat for cat, tmpl in _TASK_TEMPLATES.items()}
issues = detect_product_issues(recent, pool_sig_to_cat)
print(f'\nDetected {len(issues)} issues:')
for i in issues:
    print(f'  [{i["severity"]}] {i["issue_type"]}: {i["title"][:70]}')

nxt = pick_next_category(recent)
nxt_sig = _TASK_TEMPLATES[nxt]['duplicate_signature']
print(f'\nNext category: {nxt}')
print(f'  signature: {nxt_sig}')
print(f'  in cooldown: {nxt_sig in sigs}')
