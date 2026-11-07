from pathlib import Path
import sys,json,copy
R=Path(__file__).resolve().parent
base=Path(r'D:\fifaol3\chain-round-buy\test_client.py').read_text('utf8').split("report=json.loads")[0]
base=base.replace("elif op in (0x09,0x1d):pass", "elif op in (0x02,0x09,0x1d):pass")
# The replay VM is loaded from source by the previous test helper, so add NOP there too.
base=base.replace("source=source.replace('elif op==0xa9:'", "source=source.replace('elif op in (0x09,0x1d):pass','elif op in (0x02,0x09,0x1d):pass')\nsource=source.replace('elif op==0xa9:'")
exec(compile(base,'native-chain-replay','exec'),globals())
a=ABC((R/'list.updated.abc').read_bytes());checks=[]
def fixture():
 label=dict(x=1009,y=4,width=220,alpha=1,listeners={},rectangles=[]);label['validateNow']=lambda:None
 def clear():label['rectangles'].clear()
 label['graphics']=dict(clear=clear,beginFill=lambda *args:None,drawRect=lambda *args:label['rectangles'].append(args),endFill=lambda:None)
 label['addEventListener']=lambda e,f:label['listeners'].__setitem__(e,f)
 owner=dict(_chainRoundState=None,data={},countLabel=label,titleLabel=dict(x=382,width=500),children=[])
 return owner,UI(a,owner),label
def bind(vm,owner,data):owner['data']=data;vm.run(4,[data],start=206)
event=dict(stopImmediatePropagation=lambda:None);data=dict(shopid=71350401,round_buy_supported=True,round_buy_enabled=True)
o,v,label=fixture();bind(v,o,data);assert label['visible'] and label['mouseEnabled'] and label['text']=='【一键购买本轮】';assert not o['children'];assert label['rectangles']==[(0,0,190,27)];assert label['x']==1009 and label['width']==190 and label['scaleX']==label['scaleY']==1
bind(v,o,data);assert len(label['listeners'])==2 and set(label['listeners'])=={'click','mouseDown'} and label['mouseChildren'] is False and label['hitArea'] is None and label['useHandCursor'] and label['rectangles']==[(0,0,190,27)];checks.append('Original native countLabel displays and handles the one-click action without a dynamic Sprite or platform font TextField')
click=label['listeners']['click'];press=label['listeners']['mouseDown'];assert label['mouseEnabled'] and any(x<=95<x+w and y<=13<y+h for x,y,w,h in label['rectangles']);v.run(press.mid,[event]);v.run(click.mid,[event]);assert len(v.puts)==1 and v.puts[-1]['uri']=='/shop/chain/round/quote?root=71350401'
quote=dict(root=71350401,signature='signed-current-round',nonce='only-in-memory')
v.run(v.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,quote=quote,message='本轮总价'))]);dialog=v.dialogs[-1];v.run(dialog['buttonHandler'].mid,[dict(type='cancel')]);assert len(v.puts)==1 and not o['_chainRoundState']['busy'];checks.append('Repeated click coalesces; cancellation makes no purchase')
v.run(click.mid,[event]);v.run(v.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,quote=quote,message='本轮总价'))]);v.run(v.dialogs[-1]['buttonHandler'].mid,[dict(type='ok')]);assert v.puts[-1]['body']==dict(quote=quote)
v.run(v.puts[-1]['handlers']['error'].mid,[{}]);assert label['text']=='重试本轮购买';n=len(v.puts);v.run(click.mid,[event]);assert len(v.puts)==n+1 and v.puts[-1]['body']==dict(quote=quote)
v.run(v.puts[-1]['handlers']['complete'].mid,[dict(body=dict(result=True,message='本轮完成'))]);assert 'refresh' in v.calls and not o['_chainRoundState']['busy'];checks.append('Explicit confirmation, identical receipt-key retry and success refresh remain intact')
bind(v,o,dict(data,round_buy_enabled=False));assert not label['mouseEnabled'];n=len(v.puts);v.run(click.mid,[event]);assert len(v.puts)==n
bind(v,o,dict(shopid=70000001));assert not label['mouseEnabled'] and not label['buttonMode'];checks.append('Disabled and unsupported rows cannot submit quotes')
a2=ABC((R.parent/'chain-ui-fix/tile.updated.abc').read_bytes());using=dict(visible=False);buy=dict(visible=True);owner=dict(usingIcon=using,buyButton=buy,children=[using])
def add(child):
 if child in owner['children']:owner['children'].remove(child)
 owner['children'].append(child);return child
owner['addChild']=add;vm=UI(a2,owner)
for step in ('default','activity','complete','complete','activity','complete'):
 vm.run(12,[dict(currentstep=step)],start=1829)
 assert using['visible']==(step=='complete')
 if step=='complete':assert using['text']=='购买完成' and owner['children'][-1] is using and not buy['visible'] and using['y']==162
assert len(owner['children'])==1;checks.append('Purchased stages show native 购买完成 above masks; renderer reuse hides old completion and never duplicates controls')
# Operand/scope and branch-join validation of full modified list methods and inserted completion tail.
stack_source=(HELP/'verify_stacks.py').read_text('utf8').split('results={}')[0]
stack_source=stack_source.replace('op in (0x46,0x4a,0x4f)','op in (0x45,0x46,0x4a,0x4f)').replace('elif op==0x55:', 'elif op==0x87:pops=2;pushes=1\n        elif op==0x56:pops=operand();pushes=1\n        elif op==0x55:').replace('(0x08,0x09,0x10,0x47','(0x02,0x08,0x09,0x10,0x47')
ns={'__file__':str(HELP/'verify_stacks.py')};exec(stack_source,ns)
stacks={str(i):ns['check'](a,i) for i in (4,7,8,9,10,11)}
a2.A['body'][12]=a2.A['body'][12][1829:];stacks['completion_tail']=ns['check'](a2,12)
report=dict(status='PASS',checks=checks,stacks=stacks,native_verified=False)
(R/'client-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(dict(status='PASS',checks=len(checks),stack_methods=len(stacks))))
