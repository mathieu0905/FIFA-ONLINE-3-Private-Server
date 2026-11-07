"""Client-only style release, preserving the latest parent's full verifier policies."""
from pathlib import Path
src=(Path(__file__).parent/'install_batch.py').read_text('utf8')
src=src.replace("EXPECTED_PAGE='2555f22d92b0e7b0bcc29da37be1e1082271bdcad7d38dda6ba290e29fd0644c'","EXPECTED_PAGE='7f0b691671a06ba1d551afb1117f0936c9081449cc55aec48563322fe947e032'")
src=src.replace("assert sha(page)=='8b72154883406f94b68d5411ab7e9e5e9fa467676c7f4e34c55e2296090b93d8'","assert sha(page)=='657e82a5e3af97869e85b4d0050e35a2717deda7e0c5f582b7be7d75bb77be04'")
src=src.replace("O/'batch-bound-v1'","O/'native-style-v6'")
start=src.index("    code=(S/'patches/exp_selection_preflight.py')")
end=src.index("    compile(code",start)
src=src[:start]+'''    # Copy the current complete gate implementation, including mutable-market
    # seed checks; inheriting file hashes alone would drop this newer policy.
    code=(S/old).read_text('utf8')
    prior_status=json.loads((S/parent.RECEIPT).read_text('utf8'))['status']
    for before,after in ((parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(parent.SELF,HELPER),(prior_status,'INSTALLED_EXP_STYLE'),(verified['status'],'EXP_STYLE_PREFLIGHT_PASS')):
        assert before in code, 'Unrecognized parent gate; retain all policies before rebasing'
        code=code.replace(before,after)
'''+src[end:]
src=src.replace('exp_batch','exp_style').replace('exp-batch','exp-style').replace('EXP_BATCH','EXP_STYLE')
src=src.replace("(O/'batch-install-result.json')","(O/'native-style-install-result.json')")
src=src.replace("    guards=composition['guards'];seen=set()", "    ledger=S/'docs/工程经验与修改边界.txt'\n    files[ledger]=ledger.read_bytes()+b'\\r\\n'+(O/'native-style-ledger.txt').read_bytes()\n    guards=composition['guards'];seen=set()")
src=src.replace('Game is running. Do not install loaded UI resources or close the user game.','更新已延后，当前游戏继续运行。客户端资源将在游戏自然退出后的安全窗口替换。')
src=src.replace("batch_scope='minus, plus, typed quantity, maximum, unified preview, expected snapshot, authoritative after/count'","style_scope='Native BlueAquaButton skin, centered compact row,64px input; known-working arithmetic and native loop marker preserved'")
exec(compile(src,str(__file__)+':atomic-style-publisher','exec'),globals())
