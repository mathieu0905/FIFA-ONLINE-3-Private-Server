"""Acquire Latin identity names from the official EA API; never use its ratings."""
import concurrent.futures,datetime,time,requests
from common import *


def main():
    bios=read(R/'source-ready.json');ids=[p['playerid'] for p in bios['cards']]
    out=R/'ea-sources';out.mkdir(exist_ok=True)
    def batch(index):
        want=ids[index:index+45];path=out/f'identity-{index}.json'
        if not path.exists():
            params=dict(locale='en',limit=100,player=','.join(map(str,want)))
            for attempt in range(3):
                try:
                    res=requests.get('https://drop-api.ea.com/rating/ea-sports-fc',params=params,timeout=20);res.raise_for_status()
                    data=res.json();assert {p['id'] for p in data['items']}<=set(want)
                    write(path,dict(url=res.url,data=data));break
                except Exception:
                    if attempt==2:raise
                    time.sleep(.4)
        value=read(path);assert {p['id'] for p in value['data']['items']}<=set(want)
        return value
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:packets=list(ex.map(batch,range(0,len(ids),45)))
    names={p['id']:p for v in packets for p in v['data']['items']}
    manual={74574:dict(name='Lorenzo Bernasconi',url='https://www.uefa.com/newsfiles/UCL/2026/2045996_LU.pdf'),
        81724:dict(name='Camilo Durán',url='https://es.uefa.com/uefachampionsleague/clubs/players/250212186--camilo-duran/')}
    missing=[];birth_conflicts=[]
    for p in bios['cards']:
        pid=p['playerid'];name=names.get(pid)
        if name:
            full=name.get('commonName') or ' '.join(x for x in (name.get('firstName'),name.get('lastName')) if x)
            if not full:raise ValueError('Empty official Latin name')
            p['official_latin_name']=full;p['ea_identity_name_fields']={k:name.get(k) for k in ('firstName','lastName','commonName')}
            birth=datetime.datetime.strptime(name['birthdate'].split(' ')[0],'%m/%d/%Y').date().isoformat()
            if birth!=p['source_birth']:birth_conflicts.append(dict(playerid=pid,name=full,ea_birth=birth,nexon_birth=p['source_birth']))
        elif pid in manual:
            p['official_latin_name']=manual[pid]['name'];p['manual_name_source']=manual[pid]['url']
            if pid==81724:
                p['source_birth_original']=p['source_birth'];p['source_birth']='2002-02-10';p['birthdate']='2/10/2002 12:00:00 AM'
                p['birth_correction_source']=manual[pid]['url']
        elif p['name_existing']:
            p['official_latin_name']=p['name_existing']['full_eng']
        else:missing.append(dict(playerid=pid,name_ko=p['name_ko']))
    if missing:
        write(R/'names-missing.json',missing);raise ValueError('New identity Latin names unavailable: '+str(len(missing)))
    # Newly imported identity DOB disagreements require a specific reviewed resolution.
    new_ids={p['playerid'] for p in bios['cards'] if not p['native_existing']}
    new_conflicts=[p for p in birth_conflicts if p['playerid'] in new_ids]
    write(R/'ea-birth-conflicts.json',dict(all=birth_conflicts,new_identity=new_conflicts))
    if new_conflicts:raise ValueError('New identity birth disagreement; review exact names/dates before build')
    bios.update(official_latin_names=len(names),ea_identity_source='https://drop-api.ea.com/rating/ea-sports-fc?locale=en&player=...',
        ea_used_for='Names and independent identity/DOB cross-check only; no EA base-card abilities imported.',
        ea_birth_conflicts_existing_only=birth_conflicts,ea_packet_hashes={p.name:sha(p) for p in out.glob('identity-*.json')})
    write(R/'source-ready.json',bios)
    print('LATIN_NAMES_READY',len(bios['cards']),'EA matched',len(names),'new DOB conflicts',len(new_conflicts))


if __name__=='__main__':main()
