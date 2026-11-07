from pathlib import Path
P=Path(__file__).resolve().parent
def main():
 old=Path('D:/fifaol3/value-redesign-v12/install.py').read_text('utf8');prefix=old[:old.index('def plan():')]
 prefix=prefix.replace("SELF='patches/fair_value_v12_preflight.py';MANIFEST='patches/fair-value-v12-installed.json';RECEIPT='patches/fair-value-v12-receipt.json'","SELF='patches/nostalgia_value_v13_preflight.py';MANIFEST='patches/nostalgia-value-v13-installed.json';RECEIPT='patches/nostalgia-value-v13-receipt.json'")
 prefix=prefix.replace("owner='fair-value-v12'","owner='nostalgia-value-v13'")
 source=prefix+(P/'transaction.py').read_text('utf8');compile(source,'install.py','exec');(P/'install.py').write_text(source,'utf8');print('Combined official installer compiled')
if __name__=='__main__':main()
