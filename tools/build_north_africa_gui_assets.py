"""Render deterministic GUI masks from the mod's province geometry."""
from pathlib import Path
import json,struct,zipfile
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from trim_focus_paths import parse

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'gfx/interface/north_africa_capture_v1'
SCALE=3
PAD=24
ROWS=6
PALETTE={'neutral':('#a99977','#574e3e'),'green':('#579b64','#284f35'),'red':('#c15b52','#683832')}

def rgba(value):return tuple(bytes.fromhex(value.lstrip('#')))+(255,)

def asset(mask,variant):
    # Every color variant shares exactly the same alpha and geometry.
    fill,edge=PALETTE[variant]
    alpha=Image.fromarray(np.uint8(mask)*255).resize((mask.shape[1]*SCALE,mask.shape[0]*SCALE),Image.Resampling.NEAREST)
    interior=alpha.filter(ImageFilter.MinFilter(5))
    image=Image.new('RGBA',alpha.size,rgba(edge));body=Image.new('RGBA',alpha.size,rgba(fill))
    image.paste(body,(0,0),interior);image.putalpha(alpha)
    canvas=Image.new('RGBA',(alpha.width+PAD*2,alpha.height+PAD*2))
    canvas.alpha_composite(image,(PAD,PAD))
    return canvas

def main():
    assert not OUT.exists(),'Output exists; choose a new version before regenerating.'
    data=(ROOT/'map/provinces.bmp').read_bytes();offset=struct.unpack_from('<I',data,10)[0];w,h=struct.unpack_from('<ii',data,18)
    assert struct.unpack_from('<H',data,28)[0]==24 and h>0 and w*3%4==0
    pixels=np.frombuffer(data,dtype=np.uint8,offset=offset).reshape(h,w,3)[::-1]
    colors=(pixels[:,:,2].astype(np.uint32)<<16)+(pixels[:,:,1].astype(np.uint32)<<8)+pixels[:,:,0]
    definition={}
    for line in (ROOT/'map/definition.csv').read_text(encoding='utf-8-sig').splitlines():
        cells=line.split(';')
        if cells and cells[0].isdigit():definition[int(cells[0])]=cells
    province_states={}
    for path in (ROOT/'history/states').glob('*.txt'):
        for state in parse(path.read_text(encoding='utf-8-sig')):
            if state.key!='state':continue
            cores={v.value for history in state.children('history') for v in history.children('add_core_of')}
            if not cores&{'TUN','LBA','EGY'}:continue
            for block in state.children('provinces'):
                for value in block.value:
                    pid=int(value.value)
                    if definition[pid][4]=='land':
                        assert pid not in province_states
                        province_states[pid]=int(state.scalar('id'))
    rgb_to_id={int(definition[p][1])*65536+int(definition[p][2])*256+int(definition[p][3]):p for p in province_states}
    selected=np.isin(colors,list(rgb_to_id))
    ys,xs=np.where(selected);x0,x1,y0,y1=int(xs.min()),int(xs.max())+1,int(ys.min()),int(ys.max())+1
    crop=colors[y0:y1,x0:x1];index=np.zeros(crop.shape,dtype=np.int32)
    for rgb,pid in rgb_to_id.items():index[crop==rgb]=pid
    centroids={pid:float(np.where(index==pid)[0].mean()) for pid in province_states}
    # Horizontal rows advance north to south. No province is cut between rows.
    breaks=np.quantile(list(centroids.values()),np.linspace(0,1,ROWS+1))
    groups={row:[] for row in range(1,ROWS+1)}
    for pid,cy in centroids.items():groups[min(ROWS,int(np.searchsorted(breaks,cy,side='right')))].append(pid)
    assert all(groups.values())
    OUT.mkdir(parents=True)
    for directory in ['bands','provinces','previews']:(OUT/directory).mkdir()
    manifest={'region':'Tunisia, Libya, Egypt including Sinai','source':'map/provinces.bmp + history/states',
              'canvas_size':[index.shape[1]*SCALE+2*PAD,index.shape[0]*SCALE+2*PAD],
              'map_crop_top_left':[x0,y0],'map_crop_size':[x1-x0,y1-y0],'scale':SCALE,'padding':PAD,
              'order':'north_to_south','grouping':'six latitude rows balanced by province count; whole province assigned by pixel centroid',
              'palette':PALETTE,'bands':[],'provinces':[]}
    previews={v:Image.new('RGBA',tuple(manifest['canvas_size'])) for v in PALETTE}
    mixed=Image.new('RGBA',tuple(manifest['canvas_size']));coverage=np.zeros(index.shape,dtype=np.uint8)
    for row,ids in groups.items():
        mask=np.isin(index,ids);coverage+=mask
        entry={'id':f'band_{row:02}','province_ids':sorted(ids),'position':[0,0],'size':manifest['canvas_size'],'files':{}}
        for variant in PALETTE:
            im=asset(mask,variant);rel=f'bands/band_{row:02}_{variant}.png';im.save(OUT/rel);entry['files'][variant]=rel
            previews[variant].alpha_composite(im)
            if variant==('green' if row<=3 else 'red'):mixed.alpha_composite(im)
        manifest['bands'].append(entry)
    assert np.array_equal(coverage,(index>0).astype(np.uint8))
    for pid in sorted(province_states):
        mask=index==pid
        entry={'id':pid,'state_id':province_states[pid],'band':next(row for row,ids in groups.items() if pid in ids),'files':{}}
        box=None
        for variant in PALETTE:
            im=asset(mask,variant)
            current=im.getbbox()
            if box is None:box=current
            assert box==current
            cropped=im.crop(box);rel=f'provinces/province_{pid}_{variant}.png';cropped.save(OUT/rel);entry['files'][variant]=rel
        entry['position']=[box[0],box[1]];entry['size']=[box[2]-box[0],box[3]-box[1]]
        manifest['provinces'].append(entry)
    for variant,im in previews.items():im.save(OUT/f'north_africa_{variant}.png')
    mixed.save(OUT/'previews/capture_example.png')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    fontpath='C:/Windows/Fonts/segoeui.ttf';boldpath='C:/Windows/Fonts/segoeuib.ttf'
    font=ImageFont.truetype(fontpath,20);small=ImageFont.truetype(fontpath,16);bold=ImageFont.truetype(boldpath,30)
    sheet=Image.new('RGB',(1520,850),'#111c23');draw=ImageDraw.Draw(sheet)
    draw.text((40,24),'СЕВЕРНАЯ АФРИКА / КОНТРОЛЬ ТЕРРИТОРИЙ',font=bold,fill='#ecdfc4')
    draw.text((40,70),f'Тунис — Ливия — Египет  ·  {len(province_states)} провинций  ·  6 горизонтальных рядов',font=font,fill='#adbac1')
    for col,(label,im) in enumerate([('ЗЕЛЁНЫЙ',previews['green']),('КРАСНЫЙ',previews['red']),('ПРИМЕР ЗАХВАТА',mixed)]):
        thumb=im.copy();thumb.thumbnail((470,370),Image.Resampling.LANCZOS)
        x=30+col*500;draw.rounded_rectangle((x,120,x+480,550),radius=12,fill='#1d2b32')
        sheet.paste(thumb,(x+(480-thumb.width)//2,155),thumb)
        draw.text((x+20,515),label,font=font,fill='#e4d8c1')
    draw.text((40,580),'ПОЛОСЫ: С СЕВЕРА НА ЮГ',font=font,fill='#e4d8c1')
    for i,b in enumerate(manifest['bands']):
        im=Image.open(OUT/b['files']['neutral']);thumb=im.copy();thumb.thumbnail((220,170),Image.Resampling.LANCZOS)
        x=30+i*250;sheet.paste(thumb,(x,625),thumb)
        draw.text((x+12,805),f'{i+1:02}  ·  {len(b["province_ids"])} провинций',font=small,fill='#adbac1')
    sheet.save(OUT/'previews/overview.png')
    # Reopen the actual PNG files and verify variant alpha equality.
    for entry in manifest['bands']+manifest['provinces']:
        ims=[Image.open(OUT/f) for f in entry['files'].values()]
        assert all(im.mode=='RGBA' for im in ims)
        assert len({im.size for im in ims})==1
        assert len({im.getchannel('A').tobytes() for im in ims})==1
    print(json.dumps({'path':str(OUT),'provinces':len(province_states),'bands':len(groups),'canvas':manifest['canvas_size'],'png_count':len(list(OUT.rglob('*.png')))}))

if __name__=='__main__':main()
