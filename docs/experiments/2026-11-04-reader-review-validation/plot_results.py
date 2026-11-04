"""Optional aggregate figure; requires matplotlib in the plotting environment."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--summary',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
summary=json.loads(args.summary.read_text(encoding='utf-8'))
fig,axes=plt.subplots(1,2,figsize=(14,6))
fig.patch.set_facecolor('#F4F7FA')
for ax,key,title in zip(axes,['full_queue','both_models_geometry_ok'],
                        ['Full queue: 98 images','Both models measurable: 92 images']):
    rows=[r for r in summary['review_budgets']['exp1']['0.5'][key] if r['review_fraction'] in [.1,.2]]
    x=np.arange(2)
    a=ax.bar(x-.18,[r['detected'] for r in rows],.36,label='Queue: observed count',color='#006D77')
    b=ax.bar(x+.18,[r['random_expected_detected'] for r in rows],.36,label='Uniform random: exact expectation',color='#8CADD2')
    ax.bar_label(a,labels=[f"{r['detected']} / {r['n_positive']} events" for r in rows],padding=5,fontsize=11)
    ax.bar_label(b,labels=[f"{r['random_expected_detected']:.2f}" for r in rows],padding=5,fontsize=11)
    ax.set_xticks(x,[f"{r['cases_reviewed']} images reviewed\n({int(r['review_fraction']*100)}% budget, rounded up)" for r in rows])
    ax.set_title(title,fontsize=16,pad=20)
    ax.set_ylim(0,15)
    ax.set_ylabel('Baseline research events detected')
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y',alpha=.2)
    ax.set_axisbelow(True)
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.14),ncol=2,frameon=False,fontsize=11)
fig.suptitle('HyunOptic | Review budgets and missed errors',fontsize=21,fontweight='bold',y=.98)
fig.text(.5,.90,'Expert 1 reference; event = baseline failure OR min(Disc Dice, Cup Dice) < 0.5',ha='center',fontsize=11)
fig.text(.5,.065,'Exploratory reuse of 49 PAPILA patients (98 eyes). Review unit: image. Random bars are expectations, not observed user results.',ha='center',fontsize=10)
fig.text(.5,.025,'Failure-first ordering contributes to full-queue results. No clinical validation, generalization or review-time benefit established.',ha='center',fontsize=10,color='#6E4400')
fig.subplots_adjust(top=.80,bottom=.30,wspace=.23,left=.06,right=.98)
fig.savefig(args.output,dpi=160,facecolor=fig.get_facecolor())
