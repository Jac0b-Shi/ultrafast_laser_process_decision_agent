"""Journal-size vector figures from the existing frozen experiment outputs."""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/research/english/build/journal-figures';OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data/processed/agent_experiment'
NAMES={'4H碳化硅':'4H-SiC','微晶玻璃':'Glass ceramic','金刚石':'Diamond','高温合金':'Superalloy'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.5,'axes.titlesize':9,'axes.labelsize':8.5,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
def save(fig,name):
    fig.savefig(OUT/(name+'.svg'),facecolor='white');plt.close(fig)
m=pd.read_csv(DATA/'metrics.csv');p=pd.read_csv(DATA/'predictions.csv');f=pd.read_csv(DATA/'feedback.csv');s=pd.read_csv(DATA/'scoring.csv')
fig,ax=plt.subplots(figsize=(7.08,2.25));ax.set_xlim(-.12,10.12);ax.set_ylim(0,4);ax.axis('off')
for x,w,label in [(0,2.05,'Literature + records\nEquations, units, scope'),(2.65,2.05,'Knowledge mapping\nReviewed relations'),(5.3,2.05,'Compute variables\nz = phi(x; K)'),(7.95,2.05,'Grouped validation\nPredict quality y')]:
    ax.add_patch(FancyBboxPatch((x,2.5),w,1.15,boxstyle='round,pad=.05',facecolor='#e9f1ee',edgecolor='#497565'));ax.text(x+w/2,3.075,label,ha='center',va='center',fontsize=8)
for x in (2.1,4.75,7.4):ax.annotate('',xy=(x+.5,3.1),xytext=(x,3.1),arrowprops={'arrowstyle':'->','color':'#497565'})
ax.text(2,1.3,'Measured historical match?',ha='center',fontsize=8)
ax.text(7,1.3,'Yes: reuse one observed setting\nNo: rank supported new settings',ha='center',fontsize=8)
ax.annotate('',xy=(4.9,1.45),xytext=(3.8,1.45),arrowprops={'arrowstyle':'->'})
ax.annotate('',xy=(2,1.85),xytext=(1,2.4),arrowprops={'arrowstyle':'->'})
ax.annotate('',xy=(8,1.85),xytext=(9,2.4),arrowprops={'arrowstyle':'->'})
ax.text(5,.25,'Measured feedback → append record → update data version → refit',ha='center',fontsize=8)
fig.subplots_adjust(left=.015,right=.985,bottom=.03,top=.97);save(fig,'method')
wide=m.pivot(index=['material','target'],columns='variant',values='rmse');gain=(1-wide.fusion_simple/wide.raw_simple)*100
fig,ax=plt.subplots(figsize=(3.44,5.0));labels=[NAMES.get(a,a)+' / '+{'depth_um':'D','roughness_um':'R','diameter_um':'Dia'}[b] for a,b in gain.index]
ax.barh(np.arange(len(gain)),gain,color=['#287b68' if v>=0 else '#b96747' for v in gain]);ax.set_yticks(np.arange(len(gain)),labels);ax.invert_yaxis();ax.axvline(0,color='#555',lw=.7);ax.set_xticks([-100,-50,0,50]);ax.set_xlabel('Test RMSE reduction (%)');ax.grid(axis='x',alpha=.2)
fig.subplots_adjust(left=.43,right=.98,top=.98,bottom=.13);fig.text(.02,.015,'D: depth; R: roughness; Dia: diameter',fontsize=8);save(fig,'mechanism_gain')
fig,axes=plt.subplots(1,3,figsize=(7.08,2.25))
for ax,material in zip(axes,['BF33','AlSiC','ZrO2']):
    q=p.loc[(p.material==material)&(p.target=='depth_um')&(p.variant=='fusion_simple')];lo=min(q.measured.min(),q.predicted.min());hi=max(q.measured.max(),q.predicted.max())
    ax.scatter(q.measured,q.predicted,s=12,color='#287b68',alpha=.85);ax.plot([lo,hi],[lo,hi],'--',color='#888',lw=.7);ax.set_title(material);ax.set_xlabel('Measured depth (μm)');ax.set_ylabel('Predicted depth (μm)');ax.set_aspect('equal',adjustable='box')
fig.tight_layout(pad=.7,w_pad=1.1);save(fig,'prediction_parity')
fig,axes=plt.subplots(1,2,figsize=(7.08,2.5));rates=s.groupby('variant').satisfied.mean().reindex(['constraint_only','constraint_uncertainty','full_score'])
axes[0].bar(['Target','+ uncertainty','+ support'],rates*100,color=['#a6bbb3','#699487','#287b68']);axes[0].set_ylabel('Targets satisfied (%)');axes[0].set_ylim(0,40);axes[0].set_title('Held-out candidate ranking')
for mode,color in [('raw','#a1694d'),('fusion','#287b68')]:
    q=f.loc[f['mode']==mode].copy();q['relative']=q.rmse/q.groupby(['material','target']).rmse.transform('first');avg=q.groupby('fraction').relative.median();axes[1].plot(avg.index*100,avg,marker='o',label=mode.capitalize(),color=color)
axes[1].set_xlabel('Available feedback pool (%)');axes[1].set_ylabel('Median RMSE / initial RMSE');axes[1].legend(frameon=False);axes[1].set_title('Development-set feedback experiment');fig.tight_layout(pad=.8,w_pad=1.5);save(fig,'decision_feedback')
print(OUT)
