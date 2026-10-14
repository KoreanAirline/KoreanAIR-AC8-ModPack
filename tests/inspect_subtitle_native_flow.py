"""Read pinned cinematic subtitle functions; never modifies game files."""
from pathlib import Path
import mmap,struct,hashlib,json,subprocess,re
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

here=Path(__file__).resolve().parent
game=Path('E:/SteamLibrary/steamapps/common/ACE COMBAT 8/Game/Binaries/Win64/AceCombat8.exe')
expected=json.loads((here/'subtitle_evidence.json').read_text())['game_sha256']
assert hashlib.sha256(game.read_bytes()).hexdigest()==expected
with game.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
    pe=struct.unpack_from('<I',data,0x3c)[0]
    count=struct.unpack_from('<H',data,pe+6)[0];optional=struct.unpack_from('<H',data,pe+20)[0]
    sections=[]
    for i in range(count):
        at=pe+24+optional+40*i
        size,rva,raw_size,raw=struct.unpack_from('<IIII',data,at+8)
        sections.append((rva,max(size,raw_size),raw))
    def read(rva,n):
        section=next(s for s in sections if s[0]<=rva<s[0]+s[1])
        offset=section[2]+rva-section[0]
        return data[offset:offset+n]
    lines=[]
    lines.append('lowered-display option-key bytes: '+read(0xCBB4820,80).hex())
    option_name=read(0xCBB4820,62).decode('utf-16-le').rstrip('\0')
    assert option_name=='Display_SpeakerNameSubtitlesOn'
    lines.append('lowered-display option-key UTF16: '+option_name)
    md=Cs(CS_ARCH_X86,CS_MODE_64)
    dispatch=list(md.disasm(read(0x7A652B7,0x27),0x147A652B7))
    assert dispatch[0].mnemonic=='movzx' and dispatch[0].op_str=='ecx, byte ptr [rdx + 0xc0]'
    assert any(i.mnemonic=='je' and i.op_str=='0x147a65ca3' for i in dispatch)
    assert any(i.mnemonic=='jne' and i.op_str=='0x147a65d1a' for i in dispatch)
    free_position=list(md.disasm(read(0x7A65633,0x38),0x147A65633))
    assert any(i.mnemonic=='mulsd' and i.op_str=='xmm1, qword ptr [rax + 0x80]' for i in free_position)
    assert any(i.mnemonic=='mulsd' and i.op_str=='xmm0, qword ptr [rax + 0x88]' for i in free_position)
    assert any(i.mnemonic=='call' and i.op_str=='0x143c5d840' for i in free_position)
    main_update=list(md.disasm(read(0x7A65CA3,0x77),0x147A65CA3))
    assert not any(i.mnemonic=='call' and i.op_str=='0x143c5d840' for i in main_update)
    radio_box=read(0xC74C2B0,0x40)
    assert struct.unpack_from('<Q',radio_box,0)[0]==0x14C7578B8
    assert struct.unpack_from('<I',radio_box,0x32)[0]==0x340
    assert struct.unpack_from('<Q',radio_box,0x38)[0]==0x143CFDF30
    assert list(md.disasm(read(0x3CFDF30,5),0x143CFDF30))[0].op_str=='0x143cfda70'
    assert read(0xBA26052,24).decode('utf-16-le').rstrip('\0')=='VerticalBox'
    for rva,n in [(0x6DB5DD0,0x90),(0x6DB5E60,0xF0),(0x6DB5F80,0x340),(0x6DB5930,0xB0),(0x7A63070,0xE00),(0x7A64510,0x2300),(0x6DBB0D0,0x240)]:
        lines.append(f'function {rva:#x} sha256={hashlib.sha256(read(rva,n)).hexdigest()}')
        for ins in md.disasm(read(rva,n),0x140000000+rva):
            lines.append(f'{ins.address-0x140000000:08x} {ins.mnemonic} {ins.op_str}')
    # Native registration/property descriptors delimit cinematic class fields.
    for rva,n in [(0xC610800,0x600),(0xC612000,0x600)]:
        lines.append(f'data {rva:#x}')
        for off in range(0,n,16):
            lines.append(f'{rva+off:08x} {read(rva+off,16).hex()}')
    (here/'subtitle_native_flow.txt').write_text('\n'.join(lines))
    pins={f'{rva:#x}:{size:#x}':hashlib.sha256(read(rva,size)).hexdigest()
          for rva,size in [(0x7A652B7,0x27),(0x7A65633,0x38),(0x7A65CA3,0x77),(0x7A63DCC,0x2A),(0xCBB4820,62),
                           (0xC74C2B0,0x40),(0x3CFDF30,5),(0xBA26052,24)]}
runtime=here.parent/'runtime'
result=subprocess.check_output([str(runtime/'tools/lua.exe'),str(runtime/'lua_subtitle_test.lua'),str(runtime)],text=True)
matched=re.search(r'Subtitle module: (\d+) checks passed',result)
assert matched and int(matched[1])>=95
(runtime/'build/lua_subtitle_test.txt').write_text(result)
report={
    'passed':True,'game_sha256':expected,'native_slice_sha256':pins,
    'source_sha256':{str(p.relative_to(here.parent)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in [runtime/'scripts/subtitle.lua',runtime/'lua_subtitle_test.lua']},
    'native_findings':{'position_rate_scope':'Free-position cinematic caption option only; the main caption branch does not call SetPosition.',
                       'lowered_flag_option':option_name,
                       'radio_box':'Native RadioBox at offset0x340 is a VerticalBox. Only the exact box under RadioPanel containing both exact radio text references is eligible for a compact Canvas slot.'},
    'checks':int(matched[1]),'test_log':'runtime/build/lua_subtitle_test.txt',
    'native_layout_rule':'Exact Main/Local text or compact radio dialogue Canvas slots receive normalized bottom anchors. Four measured corners must prove axis-aligned full viewport vertical extent, allowing a horizontally inset16:9 parent and different UMG DPI local units. Authored horizontal fields are retained. Cached native fields are checked for caption resets; stable anchors require no geometry or setter calls.',
    'fallback':'Unknown or authored stacked dialogue remains on the guarded compact-container translation route; title and free-position captions are excluded.',
    'validation_limit':'Pinned executable dispatch and actual shipped Lua fixtures were checked. No game was launched; instantiated cinematic widget slots have not been visually validated.'
}
(here/'subtitle_native_anchor_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(here/'subtitle_native_flow.txt')
