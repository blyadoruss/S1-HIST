"""Remove categories absent from the local decision roster and stale callers."""
from pathlib import Path
from collections import Counter
import json,re,zipfile,sys
from datetime import datetime
from trim_focus_paths import parse,walk,edits_applied
from clean_removed_focus_references import ROOT,BASE,effective,prune

def inventory():
    used=set();definitions=set();changes={};sources={};removed_decisions=set()
    for p in (ROOT/'common/decisions').glob('*.txt'):
        used.update(n.key for n in parse(p.read_text(encoding='utf-8-sig'))
                    if isinstance(n.value,list) and n.value and not n.key.startswith('@'))
    for p in (ROOT/'common/decisions/categories').glob('*.txt'):
        definitions.update(n.key for n in parse(p.read_text(encoding='utf-8-sig')) if isinstance(n.value,list))
    removed=definitions-used
    for rel,p in effective('common/decisions').items():
        text=p.read_bytes().decode('utf-8-sig');nodes=parse(text)
        gone=[n for n in nodes if n.key in removed]
        if not gone:continue
        if 'categories' not in rel.parts:
            removed_decisions.update(c.key for n in gone for c in n.value if isinstance(c.value,list))
        changes[rel]=edits_applied(text,[(n.start,n.end,'') for n in gone])
        sources[rel]=p
    return used,removed,removed_decisions,changes,sources

TRIGGERS={'has_active_mission','has_decision','has_completed_decision','has_available_decision'}
EFFECTS={'activate_mission','remove_mission','activate_decision','remove_decision','unlock_decision_tooltip','activate_mission_tooltip','unlock_decision_category_tooltip','decision_category'}

def strip_callers(text,ids):
    edits=[]
    def visit(n):
        if isinstance(n.value,str):
            if n.value.strip('"') in ids:
                if n.key in TRIGGERS:edits.append((n.start,n.end,'always = no'))
                elif n.key in EFFECTS:edits.append((n.start,n.end,''))
        elif any(isinstance(c.value,str) and c.value.strip('"') in ids and c.key in {'decision','mission'} for c in n.value):
            assert n.key in {'unlock_decision_tooltip','activate_targeted_decision','activate_decision','add_days_mission_timeout','add_days_remove','remove_targeted_decision'}, n.key
            edits.append((n.start,n.end,''))
        else:
            for c in n.value:visit(c)
    for n in parse(text):visit(n)
    return (prune(edits_applied(text,edits)) if edits else text),len(edits)

def main(apply):
    used,cats,decisions,changes,sources=inventory()
    print('Categories removed:',len(cats),'decision definitions disabled:',len(decisions),'roster files:',len(changes),flush=True)
    ids=cats|decisions
    pat=re.compile(r'\b(?:'+'|'.join(TRIGGERS|EFFECTS|{'decision','mission'})+r')\s*=\s*"?(?:'+'|'.join(map(re.escape,sorted(ids)))+r')\b')
    counts={}
    for folder in ['common','events','history']:
        for rel,p in effective(folder).items():
            text=changes.get(rel)
            if text is None:text=p.read_bytes().decode('utf-8-sig')
            if not pat.search(re.sub(r'#[^\n]*','',text)):continue
            try:updated,count=strip_callers(text,ids)
            except Exception:
                print('Failed file:',p,flush=True);raise
            if count:
                changes[rel]=updated;sources[rel]=p;counts[str(rel)]=count
                assert not pat.search(re.sub(r'#[^\n]*','',updated)),rel
                print(rel,count,flush=True)
    # Validate the effective category/decision roster before writing.
    defined=set();decision_categories=set();original_defined=set();original_categories=set()
    for rel,p in effective('common/decisions').items():
        text=changes.get(rel,p.read_bytes().decode('utf-8-sig'))
        ns=parse(text)
        target=defined if 'categories' in rel.parts else decision_categories
        target.update(n.key for n in ns if isinstance(n.value,list) and (n.value or 'categories' in rel.parts))
        original_target=original_defined if 'categories' in rel.parts else original_categories
        original_target.update(n.key for n in parse(p.read_text(encoding='utf-8-sig')) if isinstance(n.value,list) and (n.value or 'categories' in rel.parts))
    assert not cats & defined
    assert (decision_categories-defined)<=(original_categories-original_defined),sorted(decision_categories-defined)
    assert used<=defined,sorted(used-defined)
    for rel,text in changes.items():parse(text)
    if apply:
        backup=ROOT/'tools'/('before_decision_category_cleanup_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.zip')
        manifest={'removed_categories':sorted(cats),'removed_decisions':sorted(decisions),'changed_files':[str(r) for r in changes],'added_files':[str(r) for r in changes if not (ROOT/r).exists()],'cleaned_callers':counts,'backup':str(backup.relative_to(ROOT))}
        with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as z:
            for rel in changes:z.write(sources[rel],str(rel))
            z.writestr('manifest.json',json.dumps(manifest,indent=2))
        for rel,text in changes.items():
            p=ROOT/rel;p.parent.mkdir(parents=True,exist_ok=True)
            original=sources[rel].read_bytes()
            if not text.strip():text='# S1-HIST: intentionally empty override; no retained decision categories.\n'
            data=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
            p.write_bytes(data);assert p.read_bytes()==data
        (ROOT/'tools/decision_category_cleanup_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Validated',len(changes),'files; removed',len(cats),'categories; preserved',len(used),'local categories; cleaned',sum(counts.values()),'callers.',flush=True)

if __name__=='__main__':
    main('--apply' in sys.argv)
