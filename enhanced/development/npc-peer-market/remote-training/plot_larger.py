from pathlib import Path
import sys,json,argparse
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'analysis-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
R=P/'large-results';report=json.loads((R/'training-report.json').read_text('utf8'));audit=json.loads((R/'overfit-audit.json').read_text('utf8'))
font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc');colors=['#2563eb','#0891b2','#e58a2b'];labels=['2.2万参数','44.7万参数','174.5万参数'];keys=['small_long','medium_long','large_long']
fig,axes=plt.subplots(1,2,figsize=(11,4.3),dpi=160)
for key,label,color in zip(keys,labels,colors):
 run=report['runs'][key+'_2026'];hist=run['history'];axes[0].plot([x['epoch'] for x in hist],[x['validation_log_mae'] for x in hist],label=label,color=color,linewidth=1.1)
 axes[0].scatter(run['best_epoch'],run['validation']['log_mae'],color=color,s=35,zorder=5)
axes[0].set_ylim(.9,1.08);axes[0].set_xlabel('训练轮数',fontproperties=font);axes[0].set_ylabel('验证集对数绝对误差（越低越好）',fontproperties=font);axes[0].set_title('扩大网络与延长训练的实际效果',fontproperties=font);axes[0].legend(prop=font);axes[0].grid(alpha=.2)
x=list(range(3));tr=[audit[k+'_2026']['train']['log_mae'] for k in keys];va=[audit[k+'_2026']['validation']['log_mae'] for k in keys]
axes[1].bar([v-.18 for v in x],tr,width=.36,label='训练集',color='#64748b');axes[1].bar([v+.18 for v in x],va,width=.36,label='验证集',color='#e58a2b');axes[1].set_xticks(x,labels,fontproperties=font);axes[1].set_ylim(0,1.1);axes[1].set_ylabel('最佳检查点对数绝对误差',fontproperties=font);axes[1].set_title('训练拟合与未见球员验证',fontproperties=font);axes[1].legend(prop=font);axes[1].grid(axis='y',alpha=.2)
fig.tight_layout(rect=(0,.07,1,1));fig.text(.02,.015,'同一球员分组划分、同一39项属性输入；圆点为验证最佳轮次。图示使用各档seed2026，最终选型使用双种子集成。',fontproperties=font,fontsize=8)
fig.savefig(R/'capacity-training-comparison.png');print(R/'capacity-training-comparison.png')
