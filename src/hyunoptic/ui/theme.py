"""Workspace visual theme: colour tokens, chart palette and Streamlit CSS."""
from __future__ import annotations

import streamlit as st

# Categorical slots validated for CVD separation (dataviz validator, light surface).
# Colour follows the entity everywhere in the app.
SCORE_COLORS = {
    "combined_candidate_score": "#2a78d6",
    "candidate_vcdr": "#eb6834",
    "mask_q95": "#1baf7a",
}
SCORE_LABELS = {
    "combined_candidate_score": "Combined QC score",
    "candidate_vcdr": "vCDR baseline",
    "mask_q95": "Mask Q95 (negative control)",
}
DATASET_COLORS = {"PAPILA": "#6250d6", "Chákṣu": "#eda100"}

# Overlay colours (image annotations, not charts).
DISC_COLOR = "#22C55E"
CUP_COLOR = "#2F7BEA"
HIGH_CONTRAST = {"disc": "#FFD400", "cup": "#00A2FF"}
EXPERT_COLORS = ("#EF4444", "#F59E0B", "#8B5CF6", "#92400E", "#EC4899")

TEXT_SIZES = {"Standard": 15, "Large": 17, "Extra large": 19}

_CSS = """
<style>
:root{--hz-primary:#0B5CAD;--hz-primary-2:#1D6FD8;--hz-ink:#0F1B2D;--hz-ink-2:#3B4A5E;
--hz-muted:#66768A;--hz-line:#E1E7EF;--hz-surface:#FFFFFF;--hz-bg:#F5F8FC;--hz-soft:#EAF2FC;
--hz-ok:#0E7A3E;--hz-ok-bg:#E3F5EA;--hz-warn:#8A5300;--hz-warn-bg:#FFF2D6;--hz-bad:#B42318;
--hz-bad-bg:#FDE8E7;--hz-info:#0B5CAD;--hz-info-bg:#E6F0FB;--hz-base:__BASE__px}
html,body,[data-testid="stAppViewContainer"]{font-size:var(--hz-base)}
[data-testid="stAppViewContainer"]{background:var(--hz-bg)}
[data-testid="stHeader"]{background:transparent;height:2.5rem}
[data-testid="stMainBlockContainer"]{padding-top:1.2rem;padding-bottom:3rem;max-width:1500px}
[data-testid="stSidebar"]{background:#F3F7FB;border-right:1px solid var(--hz-line)}
[data-testid="stSidebarNav"] a{border-radius:10px;padding:.45rem .7rem;margin:1px 0}
[data-testid="stSidebarNav"] a span{font-size:1rem;color:var(--hz-ink-2)}
[data-testid="stSidebarNav"] a[aria-current="page"]{background:#DDEAFB;box-shadow:inset 3px 0 0 var(--hz-primary)}
[data-testid="stSidebarNav"] a[aria-current="page"] span{color:var(--hz-primary);font-weight:600}
[data-testid="stNavSectionHeader"]{text-transform:uppercase;letter-spacing:.06em;font-size:.75rem;color:var(--hz-muted)}
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > [data-testid="stVerticalBlock"]){border-radius:14px}
[data-testid="stVerticalBlockBorderWrapper"]{background:var(--hz-surface);border-color:var(--hz-line)!important;border-radius:14px}
h1,h2,h3{color:var(--hz-ink);letter-spacing:-.01em}
.hz-top{display:flex;align-items:center;gap:.9rem}
.hz-brand{display:flex;align-items:center;gap:.6rem;white-space:nowrap}
.hz-brand b{font-size:1.65rem;color:#0A2540;line-height:1}
.hz-brand small{display:block;color:var(--hz-ink-2);font-size:.9rem;margin-top:.15rem}
.hz-chip{display:flex;align-items:center;gap:.55rem;border:1px solid var(--hz-line);background:var(--hz-surface);
border-radius:12px;padding:.45rem .8rem;min-height:3.1rem}
.hz-chip b{display:block;font-size:.92rem;color:var(--hz-ink);font-weight:600;line-height:1.2}
.hz-chip small{display:block;font-size:.78rem;color:var(--hz-muted);line-height:1.2;white-space:nowrap}
.hz-dot{width:.7rem;height:.7rem;border-radius:50%;flex:none;background:#A7B3C2}
.hz-dot.on{background:#16A34A}.hz-dot.warn{background:#D97706}.hz-dot.bad{background:#DC2626}
.hz-chip.mode{background:var(--hz-soft);border-color:#CFE0F5}
.hz-title{display:flex;align-items:baseline;flex-wrap:wrap;gap:.4rem 1rem;margin:.2rem 0 .9rem}
.hz-title h1{font-size:2rem;margin:0;padding:0;font-weight:700}
.hz-title p{margin:0;color:var(--hz-ink-2)}
.hz-badges{margin-left:auto;display:flex;gap:.4rem}
.hz-kpi{display:flex;gap:.9rem;align-items:flex-start;background:var(--hz-surface);border:1px solid var(--hz-line);
border-radius:14px;padding:1rem 1.1rem;height:100%;min-height:7.2rem}
.hz-kpi .ic{flex:none;width:3rem;height:3rem;border-radius:12px;background:var(--hz-soft);color:var(--hz-primary-2);
display:flex;align-items:center;justify-content:center}
.hz-kpi .ic.ok{background:var(--hz-ok-bg);color:var(--hz-ok)}.hz-kpi .ic.warn{background:var(--hz-warn-bg);color:var(--hz-warn)}
.hz-kpi .ic.bad{background:var(--hz-bad-bg);color:var(--hz-bad)}
.hz-kpi .lb{color:var(--hz-ink-2);font-size:.9rem}
.hz-kpi .val{font-size:1.85rem;font-weight:700;color:var(--hz-ink);line-height:1.15;margin:.1rem 0;
font-variant-numeric:tabular-nums;word-break:break-word}
.hz-kpi .val.ok{color:var(--hz-ok)}.hz-kpi .val.warn{color:var(--hz-warn)}.hz-kpi .val.bad{color:var(--hz-bad)}
.hz-kpi .val.sm{font-size:1.15rem;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.hz-kpi .sub{color:var(--hz-muted);font-size:.85rem}
.hz-kpi.cmp{display:block;padding:.85rem .9rem}.hz-kpi.cmp .top{display:flex;gap:.5rem;align-items:center}
.hz-kpi.cmp .ic{width:2.1rem;height:2.1rem;border-radius:9px}.hz-kpi.cmp .ic svg{width:18px;height:18px}
.hz-kpi.cmp .lb{font-size:.85rem;line-height:1.2}.hz-kpi.cmp .val{font-size:1.6rem;margin-top:.45rem}
.hz-kpi.cmp .val.sm{font-size:1.05rem;font-family:inherit}
.hz-delta{font-size:.9rem;font-weight:600;color:var(--hz-ink-2)}
.hz-sec h3{font-size:1.3rem;margin:0;padding:0;font-weight:700}
.hz-sec p{margin:.1rem 0 .6rem;color:var(--hz-ink-2);font-size:.92rem}
.hz-badge{display:inline-block;border-radius:999px;padding:.12rem .6rem;font-size:.8rem;font-weight:600;
border:1px solid transparent;white-space:nowrap}
.hz-badge.ok{background:var(--hz-ok-bg);color:var(--hz-ok)}.hz-badge.warn{background:var(--hz-warn-bg);color:var(--hz-warn)}
.hz-badge.bad{background:var(--hz-bad-bg);color:var(--hz-bad)}.hz-badge.info{background:var(--hz-info-bg);color:var(--hz-info)}
.hz-badge.neutral{background:#EEF2F6;color:var(--hz-ink-2)}
.hz-stat{border:1px solid var(--hz-line);border-radius:12px;padding:.8rem 1rem;background:var(--hz-surface);height:100%}
.hz-stat .hd{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:.3rem .5rem;font-weight:600;font-size:.92rem;color:var(--hz-ink)}
.hz-stat .v{font-size:2rem;font-weight:700;line-height:1.2;margin:.25rem 0 .1rem;font-variant-numeric:tabular-nums}
.hz-stat .c{color:var(--hz-ink-2);font-size:.85rem}
.hz-gauge{position:relative;height:6px;border-radius:3px;background:#E3EAF3;margin:.9rem 0 .25rem}
.hz-gauge .fill{position:absolute;left:0;top:0;bottom:0;border-radius:3px;background:var(--hz-primary-2)}
.hz-gauge .mk{position:absolute;top:50%;width:13px;height:13px;margin:-6.5px 0 0 -6.5px;border-radius:50%;
background:#0A2540;border:2px solid #fff}
.hz-gauge .th{position:absolute;top:-4px;bottom:-4px;width:2px;background:#B42318}
.hz-ticks{display:flex;justify-content:space-between;font-size:.72rem;color:var(--hz-muted)}
.hz-kv{display:grid;grid-template-columns:auto 1fr;gap:.35rem 1rem;font-size:.9rem}
.hz-kv dt{color:var(--hz-ink-2)}.hz-kv dd{margin:0;text-align:right;font-weight:600;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.hz-hash{border:1px solid var(--hz-line);border-radius:12px;padding:.8rem 1rem;height:100%;background:var(--hz-surface)}
.hz-hash .hd{display:flex;gap:.6rem;align-items:center;font-weight:600}
.hz-hash code{display:block;margin:.35rem 0 .6rem;font-size:.82rem;word-break:break-all;background:#F2F5F9;
padding:.3rem .45rem;border-radius:6px;color:var(--hz-ink)}
.hz-step{display:flex;gap:.7rem;align-items:flex-start;padding:.55rem 0;border-bottom:1px solid var(--hz-line)}
.hz-step:last-child{border-bottom:0}
.hz-step .st{flex:none;width:1.6rem;height:1.6rem;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-size:.8rem;font-weight:700;color:#fff;background:#A7B3C2}
.hz-step .st.ok{background:#16A34A}.hz-step .st.warn{background:#D97706}.hz-step .st.bad{background:#DC2626}
.hz-step>div{min-width:0}.hz-step b{display:block;font-size:.95rem}.hz-step small{color:var(--hz-ink-2);overflow-wrap:anywhere}
.hz-step .tm{margin-left:auto;color:var(--hz-muted);font-size:.8rem;white-space:nowrap}
.hz-empty{border:1px dashed #C5D2E2;border-radius:14px;padding:1.4rem;background:#FAFCFE;display:flex;gap:1rem;align-items:flex-start}
.hz-empty .ic{color:var(--hz-primary-2)}.hz-empty b{display:block;font-size:1.05rem;margin-bottom:.2rem}
.hz-empty p{margin:0;color:var(--hz-ink-2)}
.hz-note svg{flex:none}
.hz-note{border:1px solid #CFE0F5;background:var(--hz-info-bg);border-radius:12px;padding:.75rem 1rem;color:#0A2540;
display:flex;gap:.7rem;align-items:center;font-size:.92rem}
.hz-note.warn{border-color:#F3D08A;background:var(--hz-warn-bg);color:#4A2E00}
.hz-note.bad{border-color:#F5B5AF;background:var(--hz-bad-bg);color:#5C120B}
.hz-legend{display:flex;flex-wrap:wrap;gap:.3rem .9rem;font-size:.85rem;color:var(--hz-ink-2);margin:.2rem 0}
.hz-legend span{display:inline-flex;align-items:center;gap:.35rem}
.hz-legend i{display:inline-block;width:1.4rem;height:0;border-top:3px solid currentColor}
.hz-legend i.dash{border-top-style:dashed}.hz-legend i.dot{border-top-style:dotted}
.hz-swatch{display:inline-block;width:2.2rem;height:0;border-top:3px solid;vertical-align:middle;margin-top:1.1rem}
.hz-side{border:1px solid var(--hz-line);border-radius:12px;background:var(--hz-surface);padding:.8rem .9rem;margin-top:.5rem}
.hz-side b{font-size:.95rem}.hz-side p{font-size:.82rem;color:var(--hz-ink-2);margin:.4rem 0 0}
.hz-side a{display:block;font-size:.85rem;color:var(--hz-ink-2);text-decoration:none;padding:.15rem 0}
.hz-side a:hover{color:var(--hz-primary)}
table.hz-table{width:100%;border-collapse:collapse;font-size:.85rem}
table.hz-table th{background:#F4F7FB;color:var(--hz-ink-2);font-weight:600;text-align:left;padding:.5rem .6rem;
border-bottom:1px solid var(--hz-line)}
table.hz-table td{padding:.5rem .6rem;border-bottom:1px solid var(--hz-line);font-variant-numeric:tabular-nums}
table.hz-table td.n,table.hz-table th.n{text-align:right}
table.hz-table tr.hl td{background:#F2F7FE}
.hz-scroll{overflow-x:auto}
.stButton button,.stDownloadButton button{border-radius:10px}
:focus-visible{outline:3px solid #0B5CAD!important;outline-offset:2px}
@media (max-width: 900px){.hz-title h1{font-size:1.6rem}.hz-badges{margin-left:0}}
</style>
"""


def inject_theme(text_size: str = "Standard") -> None:
    base = TEXT_SIZES.get(text_size, TEXT_SIZES["Standard"])
    st.markdown(_CSS.replace("__BASE__", str(base)), unsafe_allow_html=True)
