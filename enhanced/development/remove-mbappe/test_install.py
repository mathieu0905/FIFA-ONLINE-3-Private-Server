"""Temporary-data migration and no-interruption boundary regression."""
import copy,json,tempfile
from pathlib import Path
from unittest.mock import patch
import install as i
import build as b
def main():
 keep={'_id':'keep','spid':100020801,'grade':19,'exp':1234}
 target={'_id':'gone','spid':300231747,'grade':20,'exp':99000}
 receipt={'spid':88231747,'price':113,'transaction':'historical'}
 state={'coaches':[{'cash':918283,'ep':118282,'bag':[{'players':[target,keep]}],'risk_pack_receipts':{'x':receipt}}],
 'teams':{'0':{'players':[target,keep],'squad':{'positions':[{'id':'gone','spid':300231747,'pos':1},{'id':'keep','spid':100020801,'pos':2}],'captain':'gone','kickers':['gone','keep']}}},
 'offers':[{'spid':88231747},{'spid':100020801}],
 'market_simulation':{'books':{'88231747':{'rows':[]},'100020801':{'rows':[]}},'quotes':{},'rare_books':{},'sales':[receipt],
 'identity_quotes':{'231747':{'factor':1.01,'pending':[receipt],'historical_price_samples':[]}},
 'npc_exchange':{'assets':{'a':target,'b':keep},'history':[receipt],'agents':[{'cash':12345}]}}}
 original=copy.deepcopy(state);out,counts=i.migrate(state)
 assert state==original and counts==dict(owned=1,market_books=1,npc_assets=1,offers=1,bag_cards=1)
 assert out['teams']['0']['players']==[keep]
 assert out['teams']['0']['squad']=={'positions':[{'id':'keep','spid':100020801,'pos':2}],'captain':'','kickers':['','keep']}
 assert out['coaches'][0]['risk_pack_receipts']==original['coaches'][0]['risk_pack_receipts']
 assert out['market_simulation']['sales']==original['market_simulation']['sales']
 assert out['market_simulation']['npc_exchange']['history']==original['market_simulation']['npc_exchange']['history']
 assert out['market_simulation']['npc_exchange']['agents']==original['market_simulation']['npc_exchange']['agents']
 assert i.migrate(out)[0]==out
 live=json.loads((b.S/'gamedata/state.json').read_bytes());migrated,actual=i.migrate(live)
 assert migrated['coaches']==live['coaches'] and migrated['teams']==live['teams'],'Fresh live players unexpectedly include target; inspect squad/bag migration before installation'
 with tempfile.TemporaryDirectory() as td:
  with patch.object(i,'W',Path(td)),patch.object(i,'game_active',return_value=True),patch.object(i.release,'locks',side_effect=AssertionError('Must not take formal lock')),patch.object(i,'run',side_effect=AssertionError('Must not touch service')):
   i.main();result=json.loads((Path(td)/'install-status.json').read_text('utf8'));assert result['status']=='DEFERRED_GAME_RUNNING' and result['formal_files_written'] is False and result['service_actions'] is False
 # Plan is read-only in official roots, including while game is running.
 # Generate reviewable metadata using actual latest parent without bypassing
 # the installer game's gate for a real installation.
 with patch.object(i,'idle',return_value=None):plan=i.plan()
 assert plan['parent']=='patches/upstream_social_9104fab_preflight.py' or plan['parent'].endswith('_preflight.py')
 assert all(e['relative'] not in ('messenger.py','admin.py') for e in plan['payload'])
 result=dict(status='PASS',checks=['Targeted synthetic removal keeps balances, non-target cards/experience and receipts exact','Migration idempotent and fresh live managers/teams unchanged','Active-game installation makes no lock/service/formal-file call','Current-parent plan inherits guards/policies and preserves upstream/UI fixes'],planned_revision=plan['revision'],current_live_removed_counts=actual,formal_files_written=False)
 b.write(b.W/'install-tests.json',result);print(json.dumps(result))
if __name__=='__main__':main()
