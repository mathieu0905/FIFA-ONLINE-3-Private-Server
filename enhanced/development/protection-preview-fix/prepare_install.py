from pathlib import Path
import hashlib,json
R=Path(__file__).parent;S=Path(r'D:\FO3ID\server')
s=Path(r'D:\fifaol3\legacy-chain-hide\install.py').read_text('utf8')
s=s.replace("SELF='patches/legacy_chain_preflight.py';MANIFEST='patches/legacy-chain-installed.json';RECEIPT='patches/legacy-chain-receipt.json'", "SELF='patches/protection_preview_fix_preflight.py';MANIFEST='patches/protection-preview-fix-installed.json';RECEIPT='patches/protection-preview-fix-receipt.json'")
s=s.replace("ALLOWED={'http_config.py','legacy_chain_hide.py',SELF,MANIFEST,RECEIPT,'play-local.bat'}", "ALLOWED={'enhancement_protection40.py',SELF,MANIFEST,RECEIPT,'play-local.bat'}")
a=s.index(" source=(S/'patches/exp_selection_preflight.py')")
b=s.index(' compile(source,SELF',a)
s=s[:a]+''' source=parent_path.read_text('utf8')
 parent_status=read(server/parent.RECEIPT)['status']
 for old,new in [(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,SELF),(parent_status,'INSTALLED_PREVIEW_FIX'),(prior['status'],'PROTECTION_PREVIEW_FIX_PREFLIGHT_PASS')]:source=source.replace(old,new)
 a=source.index(' required=');b=source.index('\\n if not required<=seen:',a)
 required=source[a:b].rstrip()
 assert required.endswith('}')
 source=source[:a]+required[:-1]+",('server','enhancement_protection40.py')}"+source[b:]
'''+s[b:]
s=s.replace("'http_config.py':(R/'http_config.py').read_bytes(),'legacy_chain_hide.py':(R/'legacy_chain_hide.py').read_bytes(),", "'enhancement_protection40.py':(R/'enhancement_protection40.py').read_bytes(),")
s=s.replace("'legacy_chain_hide.py'", "'enhancement_protection40.py'")
s=s.replace("for rel in [SELF,MANIFEST,RECEIPT,'enhancement_protection40.py']:", "for rel in [SELF,MANIFEST,RECEIPT]:")
s=s.replace('legacy-chain-hide','protection-preview-fix').replace('INSTALLED_LEGACY_CHAIN_HIDE','INSTALLED_PREVIEW_FIX')
s=s.replace('Game is active; do not interrupt it','更新已延后，当前游戏继续运行')
s=s.replace('Six-file additive server transaction','Five-file additive server transaction')
s=s.replace(" server=p['server'];backup=", " closed()\n server=p['server'];backup=")
s=s.replace("   target=server/rel\n   if (target", "   closed()\n   target=server/rel\n   if (target")
s=s.replace("if __name__=='__main__':\n with locks(S):", "if __name__=='__main__':\n closed()\n with locks(S):")
compile(s,'install.py','exec');(R/'install.py').write_text(s,encoding='utf8')
# The launcher delta is generated from the actual current parent under locks;
# unrelated later layers are inherited, never pinned to an older launcher.
baseline={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [S/'enhancement_protection40.py']}
assert (S/'enhancement_protection40.py').read_bytes()==(R/'enhancement_protection40.before.py').read_bytes()
(R/'baseline.json').write_text(json.dumps(baseline,indent=2),encoding='utf8')
print('Prepared additive install inheriting current seed verification and all guards')
