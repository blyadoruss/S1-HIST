"""Trim alternative political branches while preserving shared focus dependencies."""
from pathlib import Path
import re
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r'#[^\n]*|"(?:\\.|[^"\\])*"|[{}=]|[^\s{}=#"]+')

class Node:
    def __init__(self, key, value, start, end):
        self.key, self.value, self.start, self.end = key, value, start, end
    def children(self, key):
        return [n for n in self.value if n.key == key] if isinstance(self.value, list) else []
    def scalar(self, key, default=None):
        return next((n.value for n in self.children(key)), default)

def parse(text):
    tokens = [m for m in TOKEN.finditer(text) if not m[0].startswith('#')]
    def group(i, nested=False):
        nodes = []
        while i < len(tokens):
            t = tokens[i]
            if t[0] == '}':
                assert nested, 'Unexpected closing brace'
                return nodes, i + 1
            if i + 1 < len(tokens) and tokens[i+1][0] == '=':
                key = t[0]
                i += 2
                if tokens[i][0] == '{':
                    value, i = group(i+1, True)
                    end = tokens[i-1].end()
                else:
                    value = tokens[i][0]
                    end = tokens[i].end()
                    i += 1
                nodes.append(Node(key, value, t.start(), end))
            else:
                nodes.append(Node(None, t[0], t.start(), t.end()))
                i += 1
        assert not nested, 'Unclosed brace'
        return nodes, i
    return group(0)[0]

def load():
    result = {}
    for path in sorted((ROOT / 'common/national_focus').glob('*.txt')):
        text = path.read_bytes().decode('utf-8-sig')
        trees = [n for n in parse(text) if n.key == 'focus_tree']
        focuses = [f for tree in trees for f in tree.children('focus')]
        result[path.stem] = (path, text, trees, {f.scalar('id'): f for f in focuses})
    return result

def prereqs(f):
    return [[n.value for n in p.children('focus')] for p in f.children('prerequisite')]

# These focuses are historical but originally sit behind an alternative branch.
# Keep their original availability checks and rewards.
REWIRE = {
    'BUL_form_a_regency_council': [['BUL_liberalization_of_trade_policies']],
    'SAF_commemorate_the_battle_of_blood_river': [['SAF_voortrekker_monument']],
}

def removed_paths(focuses, roots):
    removed = set(roots) & focuses.keys()
    while True:
        extra = {fid for fid, f in focuses.items() if fid not in removed
                 and any(p and all(v in removed for v in p)
                         for p in REWIRE.get(fid, prereqs(f)))}
        if not extra:
            return removed
        removed |= extra

def walk(nodes):
    for n in nodes:
        yield n
        if isinstance(n.value, list):
            yield from walk(n.value)

def edits_applied(text, edits):
    last = len(text)
    for start, end, replacement in sorted(edits, reverse=True):
        assert end <= last, ('Overlapping edits', start, end, last)
        text = text[:start] + replacement + text[end:]
        last = start
    return text

def position(fid, focuses, seen=None):
    seen = set() if seen is None else seen
    assert fid not in seen, ('Position cycle', fid)
    seen.add(fid)
    f = focuses[fid]
    x, y = int(f.scalar('x', '0')), int(f.scalar('y', '0'))
    anchor = f.scalar('relative_position_id')
    if anchor in focuses:
        px, py = position(anchor, focuses, seen)
        x, y = x + px, y + py
    return x, y

def clean_references(nodes, removed, edits):
    for n in nodes:
        if isinstance(n.value, str):
            if n.value in removed and n.key in {'has_completed_focus', 'has_focus_tree_completed', 'is_focus_available', 'has_current_focus'}:
                edits.append((n.start, n.end, 'always = no'))
            elif n.value in removed and n.key in {'complete_national_focus', 'unlock_national_focus', 'uncomplete_national_focus'}:
                edits.append((n.start, n.end, ''))
        elif n.key == 'focus_progress' and n.scalar('focus') in removed:
            edits.append((n.start, n.end, 'always = no'))
        else:
            clean_references(n.value, removed, edits)

def trim(text, trees, focuses, removed, all_removed):
    edits = []
    for tree in trees:
        for n in tree.value:
            if n.key == 'shortcut' and n.scalar('target') in removed:
                edits.append((n.start, n.end, ''))
            elif n.key != 'focus':
                continue
            elif n.scalar('id') in removed:
                edits.append((n.start, n.end, ''))
            else:
                fid = n.scalar('id')
                for field in n.value:
                    if field.key in {'prerequisite', 'mutually_exclusive'}:
                        if field.key == 'prerequisite' and fid in REWIRE:
                            replacement = ''
                            if field is n.children('prerequisite')[0]:
                                replacement = '\n\t\t'.join('prerequisite = { ' + ' '.join('focus = '+v for v in p) + ' }' for p in REWIRE[fid])
                            edits.append((field.start, field.end, replacement))
                        else:
                            refs = field.children('focus')
                            surviving = [r for r in refs if r.value not in removed]
                            if not surviving:
                                assert not refs or field.key != 'prerequisite', ('Orphan', fid)
                                edits.append((field.start, field.end, ''))
                            else:
                                edits.extend((r.start, r.end, '') for r in refs if r.value in removed)
                    elif field.key == 'relative_position_id' and field.value in removed:
                        # Resolve against the original tree before removing its anchor.
                        x, y = position(fid, focuses)
                        edits.append((field.start, field.end, ''))
                        for key, val in [('x', x), ('y', y)]:
                            coord = n.children(key)
                            assert len(coord) == 1, (fid, key)
                            edits.append((coord[0].start, coord[0].end, f'{key} = {val}'))
                    elif field.key not in {'x', 'y'}:
                        clean_references([field], all_removed, edits)
    return edits_applied(text, edits)

def validate(data):
    all_ids = {fid for _, _, _, fs in data.values() for fid in fs}
    for country, (_, _, trees, fs) in data.items():
        assert sum(len(t.children('focus')) for t in trees) == len(fs), ('Duplicate ID', country)
        for fid, f in fs.items():
            for key in ['prerequisite', 'mutually_exclusive']:
                for block in f.children(key):
                    for ref in block.children('focus'):
                        assert ref.value in fs, (country, fid, key, ref.value)
            anchor = f.scalar('relative_position_id')
            assert anchor is None or anchor in fs, (country, fid, 'anchor', anchor)
            position(fid, fs)
        for t in trees:
            for shortcut in t.children('shortcut'):
                assert shortcut.scalar('target') in fs, (country, 'shortcut', shortcut.scalar('target'))
        # Resolve AND groups of OR alternatives, rather than treating every edge as mandatory.
        reachable = set()
        while True:
            extra = {fid for fid, f in fs.items() if fid not in reachable
                     and all(any(v in reachable for v in p) for p in prereqs(f))}
            if not extra:
                break
            reachable |= extra
        assert reachable == fs.keys(), (country, 'unreachable', sorted(fs.keys() - reachable))
    return all_ids

def run_trim(apply, game_dir):
    data = load()
    config = json.loads((ROOT/'tools/historical_focus_roots.json').read_text())
    removed = {c: removed_paths(fs, config[c]) for c, (_, _, _, fs) in data.items()}
    all_removed = set().union(*removed.values())
    output = {}
    for c, (path, text, trees, fs) in data.items():
        output[path] = trim(text, trees, fs, removed[c], all_removed)
        print(f'{c}: {len(fs)} -> {len(fs)-len(removed[c])} (removed {len(removed[c])})')
    # Verify the full result in memory before any game file is written.
    candidate = {}
    for c, (path, _, _, _) in data.items():
        trees = [n for n in parse(output[path]) if n.key == 'focus_tree']
        fs = {f.scalar('id'): f for t in trees for f in t.children('focus')}
        candidate[c] = (path, output[path], trees, fs)
    validate(candidate)
    # Update existing mod consumers without changing NOT/OR/AND semantics.
    # A removed focus can never be completed, so its trigger is always false.
    for base in ['common', 'history']:
        for path in (ROOT/base).rglob('*.txt'):
            if path in output:
                continue
            text = path.read_bytes().decode('utf-8-sig')
            if not any(fid in text for fid in all_removed):
                continue
            edits = []
            clean_references(parse(text), all_removed, edits)
            if edits:
                output[path] = edits_applied(text, edits)
    # Vanilla historical plans must not queue focuses which no longer exist.
    tags = ['BUL', 'CAN', 'GER', 'HUN_ww', 'RAJ_GOE', 'ITA', 'ROM', 'SAF', 'SOV', 'ENG']
    if game_dir:
        for tag in tags:
            rel = Path('common/ai_strategy_plans')/(tag+'_historical_strategy_plan.txt')
            path = ROOT/rel
            assert not path.exists(), f'Refusing to overwrite existing AI plan: {path}'
            text = (Path(game_dir)/rel).read_bytes().decode('utf-8-sig')
            nodes = parse(text)
            edits = []
            for plan in nodes:
                for field in plan.value:
                    if field.key in ['ai_national_focuses', 'focus_factors']:
                        for entry in field.value:
                            fid = entry.value if entry.key is None else entry.key
                            if fid in all_removed:
                                replacement = 'RAJ_eastern_pakistan' if fid == 'RAJ_united_bengal' and entry.key is None else ''
                                edits.append((entry.start, entry.end, replacement))
                    else:
                        clean_references([field], all_removed, edits)
            output[path] = edits_applied(text, edits)
        # Some vanilla events complete/unlock focuses directly, including historical
        # surrender and succession events. Remove calls to deleted focuses in those
        # files while retaining the rest of the event and its historical outcomes.
        effect_pattern = re.compile(r'\b(?:complete_national_focus|unlock_national_focus|uncomplete_national_focus)\s*=\s*(\w+)')
        for directory in ['events', 'common/scripted_effects', 'common/on_actions']:
            for source in (Path(game_dir)/directory).rglob('*.txt'):
                path = ROOT/source.relative_to(game_dir)
                text = output.get(path)
                if text is None:
                    text = (path if path.exists() else source).read_bytes().decode('utf-8-sig')
                if not any(m[1] in all_removed for m in effect_pattern.finditer(text)):
                    continue
                edits = []
                clean_references(parse(text), all_removed, edits)
                if edits:
                    output[path] = edits_applied(text, edits)
    for path, text in output.items():
        parse(text)
    if apply:
        assert game_dir, '--apply requires --game-dir to update the historical AI plans'
        backup = ROOT/'tools/original_focus_trees.zip'
        assert not backup.exists(), 'Backup already exists; refusing to overwrite the original trees.'
        with zipfile.ZipFile(backup, 'w', zipfile.ZIP_DEFLATED) as z:
            for path in output:
                if path.exists():
                    z.write(path, path.relative_to(ROOT).as_posix())
        added_files = [p.relative_to(ROOT).as_posix() for p in output if not p.exists()]
        for path, text in output.items():
            bom = b'\xef\xbb\xbf' if path.exists() and path.read_bytes().startswith(b'\xef\xbb\xbf') else b''
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bom + text.encode('utf-8'))
        (ROOT/'tools/removed_focuses.json').write_text(json.dumps({c: sorted(v) for c, v in removed.items()}, indent=2)+'\n', encoding='utf-8')
        validate(load())
        (ROOT/'tools/historical_focus_changes.json').write_text(json.dumps({
            'changed_files': [p.relative_to(ROOT).as_posix() for p in output],
            'added_files': added_files,
            'backup': 'tools/original_focus_trees.zip'
        }, indent=2)+'\n', encoding='utf-8')
    print(f'Validated {sum(len(v[3]) for v in candidate.values())} surviving focuses; {len(all_removed)} removed.')

if __name__ == '__main__':
    import sys
    if '--apply' in sys.argv or '--dry-run' in sys.argv:
        game_dir = sys.argv[sys.argv.index('--game-dir')+1] if '--game-dir' in sys.argv else None
        run_trim('--apply' in sys.argv, game_dir)
        raise SystemExit
    if '--validate' in sys.argv:
        validate(load())
        print('All focus trees passed structural validation.')
        raise SystemExit
    for country, (_, text, trees, focuses) in load().items():
        if len(sys.argv) > 1 and country not in sys.argv[1:]:
            continue
        print('\n###', country, len(focuses))
        for fid, f in focuses.items():
            print(fid, ' <- ', ' & '.join('|'.join(p) for p in prereqs(f)),
                  ' EX:' + ','.join(n.value for p in f.children('mutually_exclusive') for n in p.children('focus')) if f.children('mutually_exclusive') else '')
