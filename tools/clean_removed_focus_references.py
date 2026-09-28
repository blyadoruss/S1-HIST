"""Clean references against the current effective focus catalog, not an old removal list."""
from pathlib import Path
from collections import Counter
import re
import json
import sys
import zipfile
from datetime import datetime
from trim_focus_paths import parse, walk, edits_applied

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('F:/SteamLibrary/steamapps/common/Hearts of Iron IV')

def effective(folder):
    files = {p.relative_to(BASE): p for p in (BASE/folder).rglob('*.txt')}
    files.update({p.relative_to(ROOT): p for p in (ROOT/folder).rglob('*.txt')})
    return files

def focus_ids(path):
    text=path.read_text(encoding='utf-8-sig')
    try:
        nodes=parse(text)
    except AssertionError:
        # Existing malformed vanilla joint branch; only collect its IDs, do not edit it.
        assert path.is_relative_to(BASE), path
        return set(re.findall(r'\bid\s*=\s*([A-Za-z_][\w]+)',re.sub(r'#[^\n]*','',text)))
    return {n.scalar('id') for n in walk(nodes)
            if n.key in {'focus','shared_focus','joint_focus'} and isinstance(n.value,list) and n.scalar('id')}

def catalog():
    vanilla, current = set(), set()
    for rel, path in effective('common/national_focus').items():
        ids = focus_ids(path)
        current |= ids
        vanilla |= focus_ids(BASE/rel) if path != BASE/rel and (BASE/rel).exists() else ids
    return vanilla-current, current

def candidates(deleted):
    pattern = re.compile(r'\b(?:'+'|'.join(map(re.escape,sorted(deleted)))+r')\b')
    for folder in ['common','events','history']:
        for rel,path in effective(folder).items():
            raw=path.read_bytes()
            text=raw.decode('utf-8-sig')
            if pattern.search(text):
                yield rel,path,raw,text

TRIGGERS={'has_completed_focus','has_current_focus','is_focus_available','has_focus'}
EFFECTS={'complete_national_focus','unlock_national_focus','uncomplete_national_focus'}
LISTS={'ai_national_focuses','focuses'}

def clean(text, deleted):
    nodes=parse(text)
    edits=[]
    def visit(n, parent=None):
        if isinstance(n.value,str):
            value=n.value.strip('"')
            if value in deleted:
                if n.key in TRIGGERS:
                    edits.append((n.start,n.end,'always = no'))
                elif n.key in EFFECTS or (n.key is None and parent in LISTS):
                    edits.append((n.start,n.end,''))
            if parent=='focus_factors' and n.key in deleted:
                edits.append((n.start,n.end,''))
        elif n.key=='focus_progress' and n.scalar('focus','').strip('"') in deleted:
            edits.append((n.start,n.end,'always = no'))
        else:
            for child in n.value: visit(child,n.key)
    for n in nodes: visit(n)
    if not edits:return text,0
    transformed=edits_applied(text,edits)
    return prune(transformed),len(edits)

def prune(text):
    """Fold explicit constants only; retain names of callable script definitions.

    Unknown scope rules and multi-child NOT remain untouched. False if/else_if
    branches retain their guard so later else clauses cannot change meaning.
    """
    def render(n):
        original=text[n.start:n.end]
        if isinstance(n.value,str):
            const=(n.value=='yes') if n.key=='always' and n.value in {'yes','no'} else None
            return original,const
        children=[(c,*render(c)) for c in n.value]
        mode=n.key.upper() if n.key else ''
        conjunction=mode in {'AND','LIMIT','TRIGGER','AVAILABLE','VISIBLE','ALLOWED','ENABLE','POTENTIAL','TARGET_TRIGGER','TARGET_ROOT_TRIGGER'}
        const=None
        vals=[v for _,_,v in children]
        if conjunction and False in vals:const=False
        elif conjunction and vals and all(v is True for v in vals):const=True
        elif mode=='OR' and True in vals:const=True
        elif mode=='OR' and vals and all(v is False for v in vals):const=False
        elif mode=='NOT' and len(vals)==1 and vals[0] is not None:const=not vals[0]
        if const is not None:
            value='yes' if const else 'no'
            if mode in {'AND','OR','NOT'}:return 'always = '+value,const
            return n.key+' = { always = '+value+' }',const
        if n.key in {'if','else_if'}:
            guard=next((v for c,_,v in children if c.key=='limit'),None)
            if guard is False:
                return n.key+' = { limit = { always = no } }',None
        if n.key=='text':
            guard=next((v for c,_,v in children if c.key=='trigger'),None)
            if guard is False:return '',None
        replacements=[]
        for c,rendered,value in children:
            if (mode=='OR' and value is False) or (conjunction and value is True):
                rendered=''
            if rendered!=text[c.start:c.end]:
                replacements.append((c.start-n.start,c.end-n.start,rendered))
        return edits_applied(original,replacements),None
    nodes=parse(text)
    return edits_applied(text,[(n.start,n.end,render(n)[0]) for n in nodes])

def invalid_references(text,deleted):
    hits=[]
    def visit(n,parent=None):
        if isinstance(n.value,str):
            if n.value.strip('"') in deleted and (n.key in TRIGGERS|EFFECTS or n.key=='focus' or (n.key is None and parent in LISTS)):
                hits.append(n.value)
            if parent=='focus_factors' and n.key in deleted:hits.append(n.key)
        else:
            for c in n.value:visit(c,n.key)
    for n in parse(text):visit(n)
    return hits

def run(apply=False):
    deleted,current=catalog()
    print('Current focuses:',len(current),'deleted:',len(deleted),flush=True)
    output={};sources={};counts={}
    for rel,path,raw,text in candidates(deleted):
        updated,count=clean(text,deleted)
        assert not invalid_references(updated,deleted),rel
        if count:
            # Named definitions are not deleted: callers continue to resolve.
            old=parse(text);new=parse(updated)
            assert [n.key for n in old]==[n.key for n in new],rel
            if 'scripted_localisation' in rel.parts:
                assert [n.scalar('name') for n in old]==[n.scalar('name') for n in new],rel
                for before,after in zip(old,new):
                    if before.children('text'):
                        assert after.children('text'), ('Localisation lost every variant',rel,before.scalar('name'))
            output[rel]=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf-8')
            sources[rel]=path;counts[str(rel)]=count
            print(rel,count,flush=True)
    if apply:
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        backup=ROOT/'tools'/('before_script_cleanup_'+stamp+'.zip')
        added=[str(rel) for rel in output if not (ROOT/rel).exists()]
        with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as z:
            for rel in output:z.write(sources[rel],str(rel))
            z.writestr('cleanup_manifest.json',json.dumps({'added_files':added,'references_removed':counts,'deleted_focuses':sorted(deleted)},indent=2))
        for rel,raw in output.items():
            p=ROOT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            assert p.read_bytes()==raw
        (ROOT/'tools/script_cleanup_manifest.json').write_text(json.dumps({'backup':str(backup.relative_to(ROOT)),'added_files':added,'references_removed':counts,'deleted_focuses':sorted(deleted)},indent=2)+'\n',encoding='utf-8')
    print('Validated',len(output),'files;',sum(counts.values()),'removed references.',flush=True)

if __name__ == '__main__':
    if '--apply' in sys.argv or '--dry-run' in sys.argv:
        run('--apply' in sys.argv)
        raise SystemExit
    deleted,current=catalog()
    print('Current focuses:',len(current),'deleted:',len(deleted),flush=True)
    counts=Counter()
    for rel,path,raw,text in candidates(deleted):
        nodes=parse(text)
        hits=[n for n in walk(nodes) if isinstance(n.value,str) and n.value.strip('"') in deleted]
        if hits:
            keys=Counter(str(n.key) for n in hits)
            counts.update(keys)
            print(str(rel),len(hits),dict(keys),flush=True)
    print('TOTAL',dict(counts))
