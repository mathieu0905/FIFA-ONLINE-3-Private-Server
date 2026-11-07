"""Exact-ID current official FCO ability snapshots, no enhancement/level/team boosts."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import datetime,hashlib,html,json,re,sys,time,urllib.request,urllib.parse
sys.dont_write_bytecode=True
import prepare
LABELS={'속력':'sprintspeed','가속력':'acceleration','골 결정력':'finishing','슛 파워':'shotpower','중거리 슛':'longshots',
    '위치 선정':'positioning','발리슛':'volleys','페널티 킥':'penalties','짧은 패스':'shortpassing','시야':'vision','크로스':'crossing',
    '긴 패스':'longpassing','프리킥':'freekickaccuracy','커브':'curve','드리블':'dribbling','볼 컨트롤':'ballcontrol',
    '민첩성':'agility','밸런스':'balance','반응 속도':'reactions','대인 수비':'marking','태클':'standingtackle',
    '가로채기':'interceptions','헤더':'headingaccuracy','슬라이딩 태클':'slidingtackle','몸싸움':'strength','스태미너':'stamina',
    '적극성':'aggression','점프':'jumping','침착성':'composure','GK 다이빙':'gkdiving','GK 핸들링':'gkhandling',
    'GK 킥':'gkkicking','GK 반응속도':'gkreflexes','GK 위치 선정':'gkpositioning'}
PARAMETERS=dict(n1Strong=1,n1Grow=0,n4TeamColorId=0,n4TeamColorLv=0,n4TeamColorId_Enhance=0,
    n4TeamColorLv_Enhance=0,n4TeamColorId_Feature=0,n1Change=0,strPlayerImg='')


def parse(body):
    text=body.decode('utf-8-sig')
    if '/25UCL.png' not in text:raise ValueError('Not exact 25UCL class')
    sections=re.findall(r'<ul class="data_wrap data_wrap_playerinfo">(.*?)</ul>',text,re.S)
    if not sections:raise ValueError('Missing individual stats section')
    attrs={}
    for li in re.findall(r'<li\s+class="ab"[^>]*>(.*?)</li>','\n'.join(sections),re.S):
        name=re.search(r'<div class="txt">(.*?)</div>',li,re.S)
        value=re.search(r'<div class="value[^\"]*">\s*(\d+)',li,re.S)
        if name and value:
            key=html.unescape(name[1]).strip()
            if key not in LABELS or LABELS[key] in attrs:raise ValueError('Unknown or duplicate stat '+key)
            attrs[LABELS[key]]=int(value[1])
    if len(attrs)!=34:raise ValueError('Expected 34 individual source stats, got '+str(len(attrs)))
    ovr=re.search(r'<div class="ovr value">\s*(\d+)\s*</div>',text)
    pos=re.search(r'<div class="position">\s*([A-Z]+)\s*</div>',text)
    if not ovr or not pos:raise ValueError('Missing base card summary')
    return dict(overall=int(ovr[1]),role=pos[1],attributes=attrs)


def main():
    r=prepare.ROOT;out=r/'ucl-final-source';out.mkdir(exist_ok=True)
    metadata=json.loads((r.parent/'team-balance-household/sources/spid-current.json').read_text('utf8'))
    pool=[p for p in metadata if p['id']//1000000==856]
    def one(card):
        sid=card['id'];dest=out/(str(sid)+'.html');url='https://fconline.nexon.com/datacenter/PlayerAbility'
        try:
            if not dest.exists():
                req=urllib.request.Request(url,data=urllib.parse.urlencode(dict(PARAMETERS,spid=sid)).encode(),
                    headers={'Referer':'https://fconline.nexon.com/datacenter/PlayerInfo?spid='+str(sid),'X-Requested-With':'XMLHttpRequest'})
                body=urllib.request.urlopen(req,timeout=20).read();dest.write_bytes(body);parse(body)
            body=dest.read_bytes();data=parse(body)
            row=dict(status='OK',source_spid=sid,playerid=sid%1000000,name_ko=card['name'],**data,
                url=url,parameters=dict(PARAMETERS,spid=sid),raw_sha256=hashlib.sha256(body).hexdigest())
        except Exception as exc:row=dict(status='UNAVAILABLE',source_spid=sid,error=str(exc))
        time.sleep(.1);return row
    cards=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        for f in as_completed([ex.submit(one,p) for p in pool]):
            cards.append(f.result())
            if len(cards)%60==0:print('Current official ability snapshots',len(cards),flush=True)
    initial=json.loads((r/'ucl-audit.json').read_text('utf8'))['initial_cards']
    old={p['source_spid']:p for p in initial if p['source_spid'] is not None}
    changed=[dict(spid=p['source_spid'],name=p['name_ko'],initial=old[p['source_spid']]['overall'],current=p['overall'])
        for p in cards if p['status']=='OK' and p['source_spid'] in old and p['overall']!=old[p['source_spid']]['overall']]
    result=dict(status='CURRENT_OFFICIAL_25UCL_SOURCE_COMPLETE' if all(p['status']=='OK' for p in cards) else 'PARTIAL_SOURCE_DO_NOT_IMPORT',
        source_region='Nexon Korea FC ONLINE official datacenter; not asserted to be Tencent national-server snapshot',
        final_performance_notice='https://fconline.nexon.com/news/notice/view?n4ArticleSN=6337',
        notice_effective='2026-10-29',fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        card_count=len(cards),ok=sum(p['status']=='OK' for p in cards),changed_overall_since_initial=len(changed),changes=changed,
        query_parameters=PARAMETERS,cards=sorted(cards,key=lambda p:p['source_spid']),formal_files_written=False,cards_imported=0,
        proposed_conversion='One common multiplier on final individual football ability stats, rounded once. No manual winner/finalist bonus, no ordinary extra reward.',
        multiplier_unselected=True)
    prepare.write(r/'25ucl-current-official.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('cards','changes')},ensure_ascii=True))


if __name__=='__main__':main()
