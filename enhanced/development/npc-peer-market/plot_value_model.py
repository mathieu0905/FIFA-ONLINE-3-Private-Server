from pathlib import Path
import sys,json
sys.path.insert(0,'D:/fifaol3/npc-peer-market/analysis-deps')
sys.path.insert(0,'D:/fifaol3/npc-peer-market')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np
R=Path('D:/fifaol3/npc-peer-market');rows=json.loads((R/'historical-data.json').read_text('utf8'));report=json.loads((R/'value-analysis.json').read_text('utf8'))
font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
fig,axes=plt.subplots(1,2,figsize=(11,4.5),dpi=160)
for special,color,label in ((False,'#64748b','其它赛季'),(True,'#e58a2b','传奇/特殊赛季')):
 data=[r for r in rows if (r['season'] in (23,27,30,91,93))==special]
 axes[0].scatter([r['ovr'] for r in data],[r['price'] for r in data],s=5,alpha=.35,c=color,label=label)
axes[0].set_yscale('log');axes[0].set_xlabel('主位置基础评分（未计强化加成）',fontproperties=font);axes[0].set_ylabel('历史 +1 参考价（EP，对数刻度）',fontproperties=font)
axes[0].set_title('同能力卡，历史价格可以差很多',fontproperties=font);axes[0].legend(prop=font,fontsize=8);axes[0].grid(alpha=.15)
labels=['仅按 OVR','OVR＋赛季＋位置','再加体型与属性'];keys=['ovr_only','ovr_season_position','full_attributes'];vals=[report['validation'][k]['within_2x']*100 for k in keys]
axes[1].bar(range(3),vals,color=['#64748b','#2563eb','#0891b2'],width=.6);axes[1].set_xticks(range(3),labels,fontproperties=font,fontsize=9);axes[1].set_ylim(0,100);axes[1].set_ylabel('预测误差在 2 倍以内的比例（%）',fontproperties=font);axes[1].set_title('留出未见过的球员，检验模型能否泛化',fontproperties=font)
for i,v in enumerate(vals):axes[1].text(i,v+2,f'{v:.1f}%',ha='center',fontsize=10)
axes[1].grid(axis='y',alpha=.15)
fig.tight_layout(rect=(0,.07,1,1));fig.text(.02,.015,'16,041 条有效历史价；排除已重写自定义赛季。数据包含地区/稀缺影响，不等同实测手感。',fontproperties=font,fontsize=9,color='#475569')
fig.savefig(R/'value-model-evidence.png');print(R/'value-model-evidence.png')
