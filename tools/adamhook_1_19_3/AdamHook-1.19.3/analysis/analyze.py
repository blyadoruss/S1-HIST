import sys, struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'adamhook_deps'))
import pefile, capstone
p=pefile.PE(r'F:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe', fast_load=True)
base=p.OPTIONAL_HEADER.ImageBase
data=p.get_memory_mapped_image()
cs=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
def dis(rva,size=180):
    for i in cs.disasm(data[rva:rva+size],base+rva): print(hex(i.address-base),i.mnemonic,i.op_str)
def refs(rva):
    out=[]
    for s in p.sections:
        if not s.Characteristics&0x20000000: continue
        start=s.VirtualAddress; end=start+s.Misc_VirtualSize
        for k in range(start,end-7):
            if data[k] in (0x48,0x4c) and data[k+1] in (0x8d,0x8b) and data[k+2]&0xc7==5:
                if k+7+struct.unpack_from('<i',data,k+3)[0]==rva: out.append(k)
    return out
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='verify':
        import hashlib
        assert hashlib.sha256(p.__data__).hexdigest()=='7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5'
        cs.detail=True
        expected={0x23de95:0x332f617,0x23e645:0x332f618,0x258a32:0x332f63a,
                  0x24c6be:0x332ec69,0x27d717:0x332f616,0x262dd0:0x332f628,
                  0x263652:0x332f644,0x262b50:0x332f62b,0x13dd0:0x332f62c,
                  0x13e30:0x332f631,0xe139b0:0x333cfb8,0x12a9694:0x332f260}
        for location,target in expected.items():
            ins=next(cs.disasm(data[location:location+15],base+location))
            actual=[ins.address-base+ins.size+op.mem.disp for op in ins.operands if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP]
            assert actual==[target],(hex(location),actual,hex(target))
            section=p.get_section_by_rva(target)
            assert section.Characteristics&0x80000000
        assert data[0xe16d00:0xe16d06]==bytes.fromhex('88 91 80 00 00 00')
        assert data[0xe137c0:0xe137c7]==bytes.fromhex('0f b6 81 80 00 00 00')
        print('PASS: exact executable hash, 12 RIP-relative address references, writable sections, byte-sized Tdebug at +0x80.')
    elif len(sys.argv)>1 and sys.argv[1]=='evidence':
        import hashlib
        print('SHA256',hashlib.sha256(p.__data__).hexdigest())
        cs.detail=True
        for start,size in [(0x13dd0,128),(0x12a9694,2500),(0x24b7ed0,250),(0x23de8e,14),(0x23e63e,14),(0x258a25,19),(0x24c6b7,14),(0x27d70a,19),(0x262dc9,14),(0x263645,19),(0x262b49,14)]:
            print('BLOCK',hex(start))
            for i in cs.disasm(data[start:start+size],base+start):
                if start==0x12a9694 and not ('0x52' in i.op_str or i.mnemonic=='call' or '[rip' in i.op_str): continue
                print(hex(i.address-base),i.mnemonic,i.op_str,end='')
                for op in i.operands:
                    if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
                        r=i.address-base+i.size+op.mem.disp
                        print(' ->',hex(r),repr(data[r:r+60].split(b'\0')[0]),end='')
                print()
    elif len(sys.argv)>1 and sys.argv[1]=='callbacks':
        for addr in [0x5928,0x59f5,0x8f1c,0xbcab,0x82f4,0x428a,0x7860,0x6455,0x7e60,0x65d5,0x13ddd]:
            print('REGISTRATION',hex(addr))
            for i in cs.disasm(data[addr:addr+150],base+addr):
                if i.mnemonic=='lea' and i.op_str.startswith('rax, [rip'):
                    target=i.address-base+i.size+struct.unpack('<i',i.bytes[-4:])[0]
                    if target<0x2600000:
                        print('CALLBACK',hex(target)); dis(target,220); break
    elif len(sys.argv)>1:
        dis(int(sys.argv[1],16),int(sys.argv[2]) if len(sys.argv)>2 else 240)
    else:
        for name in ['fow','allowtraits','debug','tdebug','tag','research_on_icon_click','instantconstruction','allowdiplo','instant_wargoal','instanttraining','Focus.AutoComplete','Focus.NoChecks']:
            needle=name.encode()+b'\0'; pos=0
            while (pos:=data.find(needle,pos))>=0:
                if pos and data[pos-1]!=0: pos+=1; continue
                print(name,hex(pos),'refs',*[hex(x) for x in refs(pos)])
                pos+=1
