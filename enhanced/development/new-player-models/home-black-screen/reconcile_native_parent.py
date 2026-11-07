"""Verify the completed HTTPS owner layer and its append-only engineering note.

Historical manifest/receipt bytes are never modified. The child registers the
precise appended note only after every remaining physical guard/policy passes.
"""
import json,pathlib
import install_names_route as tx
R=pathlib.Path(__file__).resolve().parent
def check(parent,S,C):
    try:return parent.preflight(S,C)
    except RuntimeError as error:
        if parent.SELF!='patches/http_disconnect_preflight.py' or 'docs/' not in str(error):raise
    handback_path=pathlib.Path('D:/fifaol3/evidence/https-peer-close/handback.json')
    h=json.loads(handback_path.read_text('utf8'));assert h['status']=='INSTALLED_LIVE_HTTPS_DISCONNECT_PASS'
    for p,digest in h['hashes'].items():assert tx.sha(p)==digest,'HTTPS owner file drift '+p
    manifest=json.loads((S/parent.MANIFEST).read_text('utf8'));receipt=json.loads((S/parent.RECEIPT).read_text('utf8'))
    assert manifest['schema']==1 and manifest['state_shop_replaced'] is False
    assert receipt['status']=='INSTALLED_HTTP_DISCONNECT' and receipt['manifest_sha256']==tx.sha(S/parent.MANIFEST) and receipt['revision']==manifest['revision']
    doc=S/'docs/工程经验与修改边界.txt';prefix=(R/'bellingham-impact/install-input/small-1').read_bytes();current=doc.read_bytes();assert current.startswith(prefix)
    suffix=current[len(prefix):];assert suffix.decode('utf8').startswith('\nFO3-024：HTTPS响应中途被对端断开刷SSLEOFError')
    assert 'http-disconnect-20261107-012407-672999' in suffix.decode('utf8')
    roots=dict(server=S,client=C);seen=set();mismatches=[]
    for g in manifest['guards']:
        root=roots[g['root']];p=(root/g['relative']).resolve();key=(g['root'],g['relative'].replace('\\','/').casefold())
        assert p.is_relative_to(root) and p!=root and key not in seen;seen.add(key)
        if tx.sha(p)!=g['sha256']:
            assert p==doc and tx.digest(prefix)==g['sha256'],'Unrecognized guard drift '+str(p)
            mismatches.append(str(p))
    assert mismatches==[str(doc)]
    for policy in manifest.get('composition',{}).get('receipt_policies',[]):
        root=roots[policy['root']];p=(root/policy['relative']).resolve();assert p.is_relative_to(root)
        data=json.loads(p.read_text('utf-8-sig'));assert {k:v for k,v in data.items() if k!='native_status'}==policy['installation_fields']
    proof=dict(status='ALL_PARENT_GUARDS_EXCEPT_EXACT_APPEND_ONLY_NOTE_PASS',parent=parent.SELF,guards=len(seen),doc=str(doc),historical_prefix_sha256=tx.digest(prefix),current_doc_sha256=tx.digest(current),append_sha256=tx.digest(suffix),append_bytes=len(suffix),completed_owner_handback=str(handback_path),completed_owner_handback_sha256=tx.sha(handback_path),historical_files_modified=False)
    out=R/'native-roster/parent-doc-reconciliation.json'
    if out.exists():assert json.loads(out.read_text('utf8'))==proof,'Parent note changed during transaction'
    else:out.write_text(json.dumps(proof,indent=2),encoding='utf8')
    return proof
