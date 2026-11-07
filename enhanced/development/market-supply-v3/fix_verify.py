from pathlib import Path
p=Path('D:/fifaol3/market-supply-v3/verify_live.py');s=p.read_text('utf8')
s=s.replace("top,latency=request('/transfer/top/50')", "pre_request=json.loads((server/'gamedata/state.json').read_text('utf8'))\ntop,latency=request('/transfer/top/50')")
s=s.replace("assert assets(after)==assets(before),'Player assets changed'", "assert assets(after)==assets(pre_request),'GET changed player assets'\noldplayers={p['id'] if 'id' in p else p['_id']:p for p in before['teams']['0']['players']}\nnewplayers={p['id'] if 'id' in p else p['_id']:p for p in after['teams']['0']['players']}\nassert all(newplayers.get(key)==value for key,value in oldplayers.items()),'Existing card changed'\nconcurrent_additions=len(newplayers)-len(oldplayers)")
s=s.replace("'player_assets_unchanged':True", "'get_preserves_player_assets':True,'all_preinstall_cards_unchanged':True,'concurrent_card_additions':concurrent_additions")
p.write_text(s,'utf8')
