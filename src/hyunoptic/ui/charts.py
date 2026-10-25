"""Altair charts with one fixed palette (colour follows the entity) and recessive axes."""
from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd

from .theme import DATASET_COLORS, SCORE_COLORS, SCORE_LABELS, STRUCTURE_COLORS

INK, MUTED, GRID = "#3B4A5E", "#66768A", "#E6EBF1"


def _style(chart: alt.Chart, height: int) -> alt.Chart:
    return (chart.properties(height=height)
            .configure_view(stroke=None)
            .configure_axis(gridColor=GRID, gridWidth=1, domainColor="#C9D3DF", tickColor="#C9D3DF",
                            labelColor=MUTED, titleColor=INK, labelFontSize=11, titleFontSize=12,
                            titleFontWeight="normal")
            .configure_legend(orient="top", labelColor=INK, labelFontSize=12, symbolSize=120,
                              title=None, padding=0, columnPadding=16)
            .configure_title(color=INK, fontSize=13, anchor="start", fontWeight=600))


def _score_scale(names: list[str]) -> alt.Scale:
    labels = [SCORE_LABELS[n] for n in names]
    return alt.Scale(domain=labels, range=[SCORE_COLORS[n] for n in names])


def grouped_bars(df: pd.DataFrame, *, group: str, value: str, title: str = "",
                 scores: list[str], height: int = 230, ymax: float = 1.0,
                 legend: bool = True) -> alt.Chart:
    """df columns: group, 'score' (internal name), value. Columns ≤24px, rounded data-ends."""
    data = df.copy()
    data["Score"] = data["score"].map(SCORE_LABELS)
    order = [SCORE_LABELS[s] for s in scores]
    base = alt.Chart(data, title=title or alt.Undefined)
    bars = base.mark_bar(size=18, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X(f"{group}:N", title=None, sort=list(dict.fromkeys(data[group])),
                axis=alt.Axis(labelAngle=0, grid=False)),
        xOffset=alt.XOffset("Score:N", sort=order),
        y=alt.Y(f"{value}:Q", title=None, scale=alt.Scale(domain=[0, ymax])),
        color=alt.Color("Score:N", scale=_score_scale(scores), sort=order,
                        legend=alt.Legend() if legend else None),
        tooltip=[alt.Tooltip(f"{group}:N"), alt.Tooltip("Score:N"),
                 alt.Tooltip(f"{value}:Q", format=".3f")],
    )
    return _style(bars, height)


def precision_recall(curves: dict[str, tuple[np.ndarray, np.ndarray]], *, height: int = 300,
                     prevalence: float | None = None) -> alt.Chart:
    rows = []
    for name, (recall, precision) in curves.items():
        rows += [{"Score": SCORE_LABELS[name], "Recall": r, "Precision": p}
                 for r, p in zip(recall, precision)]
    data = pd.DataFrame(rows)
    names = list(curves)
    order = [SCORE_LABELS[n] for n in names]
    line = alt.Chart(data).mark_line(strokeWidth=2, interpolate="step-after", strokeCap="round").encode(
        x=alt.X("Recall:Q", scale=alt.Scale(domain=[0, 1])),
        y=alt.Y("Precision:Q", title="Precision", scale=alt.Scale(domain=[0, 1.02])),
        color=alt.Color("Score:N", scale=_score_scale(names), sort=order),
        tooltip=["Score:N", alt.Tooltip("Recall:Q", format=".3f"), alt.Tooltip("Precision:Q", format=".3f")],
    )
    layers = [line]
    if prevalence is not None:
        rule = alt.Chart(pd.DataFrame({"y": [prevalence]})).mark_rule(
            color="#94A3B8", strokeDash=[4, 4], strokeWidth=1).encode(
            y=alt.Y("y:Q", title="Precision"),
            tooltip=[alt.Tooltip("y:Q", title="Chance level (prevalence)", format=".3f")])
        layers.append(rule)
    return _style(alt.layer(*layers), height)


def pr_points(scores, labels) -> tuple[np.ndarray, np.ndarray]:
    """Precision/recall at each distinct score threshold (higher score = review first)."""
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=bool)
    if y.sum() == 0:
        return np.array([0.0]), np.array([0.0])
    order = np.argsort(-s, kind="mergesort")
    s, y = s[order], y[order]
    tp = np.cumsum(y)
    k = np.arange(1, len(y) + 1)
    last = np.r_[np.nonzero(np.diff(s))[0], len(s) - 1]  # end of each tie group
    recall = np.r_[0.0, tp[last] / y.sum()]
    precision = np.r_[1.0, tp[last] / k[last]]
    return recall, precision


def histogram(values, *, threshold: float, height: int = 260) -> alt.Chart:
    data = pd.DataFrame({"diff": np.asarray(values, dtype=float)})
    hi = max(0.5, float(data["diff"].max()) if len(data) else 0.5)
    bars = alt.Chart(data).mark_bar(color="#2a78d6", cornerRadiusTopLeft=2, cornerRadiusTopRight=2,
                                    binSpacing=2).encode(
        x=alt.X("diff:Q", bin=alt.Bin(step=0.01, extent=[0, hi]), title="Absolute inter-reader vCDR difference"),
        y=alt.Y("count():Q", title="Images"),
        tooltip=[alt.Tooltip("diff:Q", bin=alt.Bin(step=0.01, extent=[0, hi]), title="Difference bin"),
                 alt.Tooltip("count():Q", title="Images")],
    )
    stats = pd.DataFrame({
        "x": [float(np.mean(data["diff"])), float(np.median(data["diff"])), threshold],
        "Line": ["Mean", "Median", "Research threshold 0.10"],
    })
    rules = alt.Chart(stats).mark_rule(strokeWidth=1.5).encode(
        x="x:Q",
        strokeDash=alt.StrokeDash("Line:N", scale=alt.Scale(
            domain=list(stats["Line"]), range=[[6, 3], [2, 2], [1, 0]])),
        color=alt.Color("Line:N", scale=alt.Scale(domain=list(stats["Line"]),
                                                  range=["#0A2540", "#0A2540", "#B42318"])),
        tooltip=["Line:N", alt.Tooltip("x:Q", format=".3f", title="Value")],
    )
    return _style(alt.layer(bars, rules), height)


def feature_boxes(df: pd.DataFrame, feature: str, *, title: str, height: int = 220) -> alt.Chart:
    """df columns: group (camera), Dataset, value."""
    domain = [d for d in DATASET_COLORS if d in set(df["Dataset"])]
    box = alt.Chart(df, title=title).mark_boxplot(size=16, extent="min-max", median={"color": "#0A2540"},
                                                 ticks=True).encode(
        x=alt.X("group:N", title=None, sort=list(dict.fromkeys(df["group"])), axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("Dataset:N", sort=domain),
        y=alt.Y("value:Q", title=None, scale=alt.Scale(zero=False)),
        color=alt.Color("Dataset:N", scale=alt.Scale(domain=domain,
                                                     range=[DATASET_COLORS[d] for d in domain])),
    )
    return _style(box, height)


def binned_structures(hists: dict[str, dict], *, height: int = 240, title: str = "") -> alt.Chart:
    """Pre-binned aggregate histograms (no per-image data) for Disc and Cup, side by side."""
    rows = []
    for structure, h in hists.items():
        edges, counts = h["bin_edges"], h["counts"]
        rows += [{"Structure": structure, "start": edges[i], "end": edges[i + 1], "Images": c}
                 for i, c in enumerate(counts)]
    data = pd.DataFrame(rows)
    domain = list(hists)
    bars = alt.Chart(data, title=title or alt.Undefined).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=alt.X("start:Q", title="Dice", scale=alt.Scale(domain=[0, 1]), bin="binned"),
        x2="end:Q",
        y=alt.Y("Images:Q", title="Images", stack=None),
        color=alt.Color("Structure:N", scale=alt.Scale(domain=domain, range=[STRUCTURE_COLORS[d] for d in domain])),
        opacity=alt.value(0.75),
        tooltip=["Structure:N", alt.Tooltip("start:Q", title="From", format=".2f"),
                 alt.Tooltip("end:Q", title="To", format=".2f"), "Images:Q"],
    )
    return _style(bars, height)


def training_curves(history: list[dict], *, height: int = 220) -> tuple[alt.Chart, alt.Chart]:
    """Two single-axis charts: validation Dice per structure, and training loss."""
    data = pd.DataFrame(history)
    dice_rows = pd.concat([
        pd.DataFrame({"epoch": data["epoch"], "Structure": "Disc", "Dice": data["val_disc_dice"]}),
        pd.DataFrame({"epoch": data["epoch"], "Structure": "Cup", "Dice": data["val_cup_dice"]}),
    ])
    dice_chart = alt.Chart(dice_rows, title="Validation Dice (expert 1)").mark_line(
        strokeWidth=2, point=alt.OverlayMarkDef(size=40)).encode(
        x=alt.X("epoch:Q", title="Epoch", axis=alt.Axis(tickMinStep=1)),
        y=alt.Y("Dice:Q", scale=alt.Scale(domain=[0, 1])),
        color=alt.Color("Structure:N", scale=alt.Scale(domain=["Disc", "Cup"],
                                                       range=[STRUCTURE_COLORS["Disc"], STRUCTURE_COLORS["Cup"]])),
        tooltip=["epoch:Q", "Structure:N", alt.Tooltip("Dice:Q", format=".3f")],
    )
    loss_chart = alt.Chart(data, title="Training loss").mark_line(strokeWidth=2, color="#3B4A5E").encode(
        x=alt.X("epoch:Q", title="Epoch", axis=alt.Axis(tickMinStep=1)),
        y=alt.Y("train_loss:Q", title="Loss", scale=alt.Scale(zero=False)),
        tooltip=["epoch:Q", alt.Tooltip("train_loss:Q", format=".4f")],
    )
    return _style(dice_chart, height), _style(loss_chart, height)
