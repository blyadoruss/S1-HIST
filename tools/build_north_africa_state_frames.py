"""Export state silhouettes as two equal horizontal GUI frames."""
from pathlib import Path
import json
import struct
import zipfile
import numpy as np
from PIL import Image
from trim_focus_paths import parse
from build_north_africa_gui_assets import asset, SCALE, PAD

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'gfx/interface/north_africa_state_frames'


def main():
    assert not OUT.exists(), 'Output already exists'
    data = (ROOT / 'map/provinces.bmp').read_bytes()
    offset = struct.unpack_from('<I', data, 10)[0]
    w, h = struct.unpack_from('<ii', data, 18)
    assert h > 0 and w * 3 % 4 == 0
    assert struct.unpack_from('<H', data, 28)[0] == 24
    pixels = np.frombuffer(data, np.uint8, offset=offset).reshape(h, w, 3)[::-1]
    colors = (pixels[:, :, 2].astype(np.uint32) << 16) + (pixels[:, :, 1].astype(np.uint32) << 8) + pixels[:, :, 0]
    definitions = {}
    for line in (ROOT / 'map/definition.csv').read_text(encoding='utf-8-sig').splitlines():
        cells = line.split(';')
        if cells[0].isdigit():
            definitions[int(cells[0])] = cells
    states = {}
    for path in (ROOT / 'history/states').glob('*.txt'):
        for state in parse(path.read_text(encoding='utf-8-sig')):
            if state.key != 'state':
                continue
            cores = {n.value for history in state.children('history') for n in history.children('add_core_of')}
            if not cores & {'TUN', 'LBA', 'EGY'}:
                continue
            ids = [int(n.value) for block in state.children('provinces') for n in block.value]
            states[int(state.scalar('id'))] = {
                'source': path.name,
                'province_ids': [p for p in ids if definitions[p][4] == 'land'],
            }
    masks = {}
    for sid, state in states.items():
        rgbs = [int(definitions[p][1]) * 65536 + int(definitions[p][2]) * 256 + int(definitions[p][3]) for p in state['province_ids']]
        masks[sid] = np.isin(colors, rgbs)
        assert masks[sid].any()
    coverage = np.sum(list(masks.values()), axis=0)
    assert coverage.max() == 1
    ys, xs = np.where(coverage)
    left, top = int(xs.min()), int(ys.min())
    right, bottom = int(xs.max()) + 1, int(ys.max()) + 1
    OUT.mkdir(parents=True)
    entries = []
    for sid in sorted(states):
        mask = masks[sid][top:bottom, left:right]
        green = asset(mask, 'green')
        red = asset(mask, 'red')
        box = green.getbbox()
        # One shared crop, with transparent padding, for both color frames.
        box = (box[0] - 3, box[1] - 3, box[2] + 3, box[3] + 3)
        green, red = green.crop(box), red.crop(box)
        fw, fh = green.size
        sheet = Image.new('RGBA', (fw * 2, fh))
        sheet.paste(green, (0, 0))
        sheet.paste(red, (fw, 0))
        filename = f'state_{sid}_green_red.png'
        sheet.save(OUT / filename)
        with Image.open(OUT / filename) as check:
            a, b = check.crop((0, 0, fw, fh)), check.crop((fw, 0, fw * 2, fh))
            assert check.mode == 'RGBA' and check.size == (fw * 2, fh)
            assert a.getchannel('A').tobytes() == b.getchannel('A').tobytes()
            assert a.tobytes() != b.tobytes()
        entries.append({'state_id': sid, **states[sid], 'file': filename,
                        'frame_size': [fw, fh], 'sheet_size': [fw * 2, fh],
                        'position': [box[0], box[1]]})
    manifest = {'frames': ['green', 'red'], 'noOfFrames': 2,
                'scale': SCALE, 'map_crop_top_left': [left, top],
                'assembly_canvas_size': [(right-left)*SCALE+PAD*2, (bottom-top)*SCALE+PAD*2],
                'states': entries}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (OUT / 'README.txt').write_text(
        'Каждый PNG: два горизонтальных кадра одинакового размера.\n'
        'Первый кадр — зелёный, второй — красный. Прозрачный фон.\n'
        'Геометрия взята из текущих history/states и map/provinces.bmp.\n'
        'Регион: Тунис, Ливия, Египет (включая Синай).\n'
        'В spriteType укажите noOfFrames = 2.\n'
        'frame_size в manifest.json — размер одного кадра; position — позиция\n'
        'стейта при сборке общей карты на assembly_canvas_size.\n', encoding='utf-8')
    archive = OUT.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(OUT.iterdir()):
            z.write(path, path.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(json.dumps({'states': len(entries), 'folder': str(OUT), 'archive': str(archive)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
