from pathlib import Path
p=Path(__file__).parent/'inspect_labels.py'
s=p.read_text('utf-8').replace('components/Label.big','components/PlayerInfoNew.big').replace("('seasonicon','seasonplate','season1')","('card','photo','season')").replace("ROOT/'labels.json'","ROOT/'playerinfo-labels.json'")
exec(compile(s,str(p),'exec'),{'__file__':str(p)})
