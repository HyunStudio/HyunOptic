"""Render the published aggregate benchmark to a NEW output path.

Requires optional matplotlib. Does not rerun a benchmark or alter frozen evidence.
"""
import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output path; frozen evidence is never overwritten')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    data=json.loads((Path(__file__).parent/'benchmark_large.json').read_text(encoding='utf-8'))
    fig,ax=plt.subplots(figsize=(9,4.8),constrained_layout=True)
    labels=['Recorded list\n0 artifact reads','Selected detail\n3 artifact reads','Strict whole-session check\n5 reads per case']
    for i,(key,label,color) in enumerate(zip(['metadata_list','selected_case','strict_list'],labels,['#1b6ca8','#009e73','#ad5d00'])):
        values=[s[key]['p95_seconds'] for s in data['sessions']]
        positions=[i-.16,i+.16]
        ax.bar(positions,values,width=.28,color=color,alpha=.9)
        for x,y,s in zip(positions,values,data['sessions']):
            ax.text(x,y*1.18,f"{s['inputs']} cases\n{y:.4f}s",ha='center',va='bottom',fontsize=9)
    ax.set_yscale('log');ax.set_ylim(.001,100)
    ax.set_xticks(range(3),labels)
    ax.set_ylabel('Sample p95 latency (seconds, logarithmic scale)')
    ax.set_title('Review operations with different verification scopes',loc='left',fontweight='bold')
    ax.grid(axis='y',alpha=.22);ax.set_axisbelow(True)
    fig.text(.02,-.025,'1024×768 synthetic repeated input; 3 repetitions. Different workloads; not human review-time savings.',fontsize=9)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,bbox_inches='tight')
    plt.close(fig)
    return 0


if __name__=='__main__':raise SystemExit(main())
