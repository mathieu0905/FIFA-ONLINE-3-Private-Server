"""Keep old generic pack pools frozen while exposing 25UCL in the market."""
from common import *

def transform(source):
    old='WHERE p.spid / 1000000 NOT IN (300,325,327) AND ovr >= ?1'
    new='WHERE p.spid / 1000000 NOT IN (300,325,327,856) AND ovr >= ?1'
    if source.count(old)!=1:raise ValueError('Fresh generic-pack query changed; review pool preservation')
    result=source.replace(old,new);compile(result,'http_config.py','exec')
    return result

def main():
    out=Path(read(R/'latest-build.json')['path']);src=(S/'http_config.py').read_bytes()
    baseline=read(out/'source-baseline.json')
    if sha(S/'http_config.py')!=baseline[str(S/'http_config.py')]:raise ValueError('HTTP source changed; rebase build')
    result=transform(src.decode('utf8')).encode('utf8');(out/'http_config.py').write_bytes(result)
    write(out/'runtime-delta.json',dict(status='PACK_POOL_PRESERVATION_READY',before=sha(S/'http_config.py'),after=sha(out/'http_config.py'),
        ordinary_card_extra_reward=0,season_bonus_added=False,old_pack_pools_preserved=True,market_new_cards=360,formal_files_written=False))
    print('RUNTIME_DELTA_READY: exact generic-pack exclusion for new 25UCL cards; no new season bonus.')

if __name__=='__main__':main()
