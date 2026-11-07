"""Restore only the newly changed PlayerListUtil ABC to its immediate baseline."""
from pathlib import Path
import datetime,json,re,sys,copy,gc
sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'all-custom-households'))
import install as tx
sys.path.insert(0,str(R.parent/'ucl25-import'))
import display
S,C=tx.S,tx.C
SELF='patches/startup_display_recovery_20261107_preflight.py'
MANIFEST='patches/startup-display-recovery-20261107-installed.json'
RECEIPT='patches/startup-display-recovery-20261107-receipt.json'

def main():
    tx.assert_idle()
    with tx.locks():
        tx.assert_idle()
        play=(S/'play-local.bat').read_bytes();parent_rel='patches/'+re.findall(rb'patches\\(\w+_preflight\.py)',play)[0].decode()
        parent=tx.prepare.load(S/parent_rel,'black_current_parent');prior=parent.preflight(S,C);comp=parent.compose_manifest(S,C)
        oldreceipt=json.loads((S/parent.RECEIPT).read_text('utf8'))
        journal=json.loads((S/'backups/25ucl-final-072-20261107-230428-125757/transaction.json').read_text('utf8'))
        original=next(e for e in journal['entries'] if e['relative']=='data/ui/libs/Module.big')
        source=Path(original['backup']);target=C/'data/ui/libs/Module.big'
        assert tx.current_hash(source)==original['before'] and tx.current_hash(target)==original['after'],'Later Module change; refuse baseline overwrite'
        _,old,_,oldtags=display.swf(source);_,new,_,newtags=display.swf(target)
        assert len(oldtags)==len(newtags)
        changed=[(a,b) for a,b in zip(oldtags,newtags) if a[2]!=b[2]]
        assert len(changed)==1
        a,b=changed[0];assert a[0]==b[0]==82
        aa=display.ABC(a[1][a[1].index(b'\0',4)+1:]);bb=display.ABC(b[1][b[1].index(b'\0',4)+1:])
        assert aa.A['cls'][0][0]==bb.A['cls'][0][0]=='PlayerListUtil'
        assert aa.A['cls']==bb.A['cls']
        assert [mid for mid,record in aa.A['body_records'].items() if record['raw']!=bb.A['body_records'][mid]['raw']]==[12,14]
        proof=dict(status='NEW_DISPLAY_DELTA_ISOLATED',changed_ABC='PlayerListUtil',methods=[12,14],all_other_ABC_and_SWF_tags_identical=True,baseline_sha256=original['before'],prior_sha256=original['after'],data_and_cards_removed=False,reason='Login-before-home black screen; isolate unproven new display bytecode; root cause requires native retry',native_status='PENDING',market_migration=json.loads((R/'market-migration.json').read_text('utf8')))
        helper=(S/parent_rel).read_text('utf8')
        for oldv,newv in [(parent.SELF,SELF),(parent.MANIFEST,MANIFEST),(parent.RECEIPT,RECEIPT),(oldreceipt['status'],'INSTALLED_STARTUP_DISPLAY_RECOVERY'),(prior['status'],'STARTUP_DISPLAY_RECOVERY_PREFLIGHT_PASS')]:
            assert oldv in helper;helper=helper.replace(oldv,newv)
        compile(helper,SELF,'exec')
        revision='startup-display-recovery-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        doc='docs/工程经验与修改边界.txt'
        note=('\r\n\r\nFO3-STARTUP-BLACK-DISPLAY-ISOLATION-20261107\r\n'
              '用户报告启动后全黑、尚未进入主页。HTTP停在外部语言包加载后，转储未发现同先前缺原生球员记录的访问异常；不能宣布已定位根因。'
              '先使用正式迁移函数将实时state市场代际从v15对齐新增25U的v16；仅清理已入账价格事件，1100条未完成采样完整归档，所有非市场资产字段及shop逐项不变。'
              '本层仅撤下刚新增的PlayerListUtil12/14两个赛季显示方法，使用该次安装前的直接基线ABC；其它Module标签逐字节一致，不撤25U球员、原生身份、户口或徽章。'
              '25U名称的专用前缀暂待重做；这是黑屏隔离修复，静态检查不代表用户启动通过。保留全部新父层guards和receipt policies，不修改历史哈希/回执，不操作GUI。\r\n').encode('utf8')
        evidence='patches/startup-display-recovery-20261107-evidence.json'
        payload=[('client','data/ui/libs/Module.big',source),('server',doc,(S/doc).read_bytes()+note),('server',evidence,tx.encoded(proof)),('server',SELF,helper.encode('utf8')),('server','play-local.bat',play.replace(parent_rel.replace('/','\\').encode(),SELF.replace('/','\\').encode()))]
        guards={(g['root'],g['relative'].replace('\\','/').casefold()):dict(g) for g in comp['guards']}
        for root,rel,body in payload:
            p=(S if root=='server' else C)/rel;key=(root,rel.casefold())
            if key in guards:assert tx.current_hash(p)==guards[key]['sha256']
            guards[key]=dict(root=root,relative=rel,sha256=tx.current_hash(body) if isinstance(body,Path) else tx.digest(body))
        policies=list(comp.get('receipt_policies',[]))
        if not any(x['relative']==parent.RECEIPT and x['root']=='server' for x in policies):policies.append(dict(root='server',relative=parent.RECEIPT,installation_fields={k:v for k,v in oldreceipt.items() if k!='native_status'}))
        comp.update(guards=list(guards.values()),receipt_policies=policies,files_verified=False);comp.setdefault('ancestry',[]).append(dict(layer='startup-display-isolation',revision=revision,native_status='PENDING'))
        manifest=dict(schema=1,revision=revision,client=str(C),state_shop_replaced=False,guards=comp['guards'],composition=comp,parent_preflight=parent_rel,parent_preflight_sha256=tx.current_hash(S/parent_rel),native_status='PENDING')
        body=tx.encoded(manifest)
        payload += [('server',MANIFEST,body),('server',RECEIPT,tx.encoded(dict(status='INSTALLED_STARTUP_DISPLAY_RECOVERY',revision=revision,manifest_sha256=tx.digest(body),state_shop_replaced=False,native_status='PENDING')))]
        entries=[]
        for root,rel,body in payload:
            p=(S if root=='server' else C)/rel
            if rel in (SELF,MANIFEST,RECEIPT,evidence):assert not p.exists()
            entries.append(dict(relative=rel,target=p,source=body,before=tx.current_hash(p),after=tx.current_hash(body) if isinstance(body,Path) else tx.digest(body)))
        entries.sort(key=lambda e:e['relative']=='play-local.bat')
        gc.collect();backup=S/'backups'/revision;backup.mkdir()
        for i,e in enumerate(entries):
            e['backup']=backup/(str(i)+'-'+e['target'].name)
            if e['before'] is not None:e['backup'].write_bytes(e['target'].read_bytes())
        written=[]
        try:
            for e in entries:
                tx.assert_idle();tx.cas(e);written.append(e)
            result=tx.prepare.load(S/SELF,'black_recovery_gate').preflight(S,C)
        except BaseException:
            tx.rollback(written);raise
        proof.update(status='DISPLAY_DELTA_WITHDRAWN_NATIVE_RETRY_PENDING',top_preflight=str(S/SELF),top_manifest=str(S/MANIFEST),top_receipt=str(S/RECEIPT),composition_api='compose_manifest(server=None,client=None)',files={str(S/p):tx.current_hash(S/p) for p in (SELF,MANIFEST,RECEIPT,'play-local.bat')},preflight_status=result['status'],guards=result['files'],backup=str(backup),GUI_used=False)
        (R/'display-recovery-installed.json').write_bytes(tx.encoded(proof));tx.atomic(tx.encoded(proof),R.parent/'root-current-top.json')
    print(json.dumps({k:proof[k] for k in ('status','top_preflight','guards','backup')}))
if __name__=='__main__':main()
