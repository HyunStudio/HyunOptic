"""HTML building blocks. All dynamic text is escaped; values are passed in, never invented."""
from __future__ import annotations

from html import escape

import streamlit as st

from .icons import icon


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def fmt(value, digits: int = 3, signed: bool = False) -> str:
    """Format a metric; None/NaN render as an explicit N/A, never as zero."""
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        return f"{value:,}"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return escape(str(value))
    if number != number:  # NaN
        return "N/A"
    return f"{number:+.{digits}f}" if signed else f"{number:.{digits}f}"


def badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="hz-badge {tone}">{escape(text)}</span>'


def page_title(title: str, subtitle: str = "", badges: list[str] | None = None) -> None:
    right = f'<div class="hz-badges">{"".join(badges)}</div>' if badges else ""
    html(f'<div class="hz-title"><h1>{escape(title)}</h1><p>{escape(subtitle)}</p>{right}</div>')


def section(title: str, subtitle: str = "") -> None:
    sub = f"<p>{escape(subtitle)}</p>" if subtitle else "<p></p>"
    html(f'<div class="hz-sec"><h3>{escape(title)}</h3>{sub}</div>')


def kpi(icon_name: str, label: str, value: str, sub: str = "", tone: str = "",
        small: bool = False, delta: str = "") -> dict:
    """value is pre-formatted text; it is escaped when rendered by kpi_row."""
    return {"icon": icon_name, "label": label, "value": value, "sub": sub, "tone": tone,
            "small": small, "delta": delta}


def _kpi_html(c: dict, compact: bool) -> str:
    cls = " ".join(x for x in (c["tone"], "sm" if c["small"] else "") if x)
    delta = f'<div class="hz-delta">{escape(c["delta"])}</div>' if c["delta"] else ""
    ic = f'<div class="ic {c["tone"]}">{icon(c["icon"])}</div>'
    body = (f'<div class="val {cls}">{escape(c["value"])}</div>{delta}'
            f'<div class="sub">{escape(c["sub"])}</div>')
    if compact:  # icon beside the label: fits six cards in a row
        return (f'<div class="hz-kpi cmp"><div class="top">{ic}<div class="lb">{escape(c["label"])}</div></div>'
                f"{body}</div>")
    return f'<div class="hz-kpi">{ic}<div><div class="lb">{escape(c["label"])}</div>{body}</div></div>'


def kpi_row(cards: list[dict]) -> None:
    compact = len(cards) > 4
    for col, card in zip(st.columns(len(cards)), cards):
        with col:
            html(_kpi_html(card, compact))


def gauge(value: float | None, lo: float, hi: float, ticks: list[float],
          threshold: float | None = None) -> str:
    if value is None:
        inner = ""
    else:
        pos = max(0.0, min(1.0, (float(value) - lo) / (hi - lo))) * 100
        inner = f'<div class="fill" style="width:{pos:.1f}%"></div><div class="mk" style="left:{pos:.1f}%"></div>'
    if threshold is not None:
        tpos = max(0.0, min(1.0, (threshold - lo) / (hi - lo))) * 100
        inner += f'<div class="th" style="left:{tpos:.1f}%" title="research threshold"></div>'
    tick_html = "".join(f"<span>{t:g}</span>" for t in ticks)
    return f'<div class="hz-gauge">{inner}</div><div class="hz-ticks">{tick_html}</div>'


def stat(label: str, value: str, caption: str = "", badge_html: str = "", extra: str = "") -> str:
    return (f'<div class="hz-stat"><div class="hd"><span>{escape(label)}</span>{badge_html}</div>'
            f'<div class="v">{escape(value)}</div><div class="c">{escape(caption)}</div>{extra}</div>')


def kv(rows: list[tuple[str, str]]) -> str:
    return '<dl class="hz-kv">' + "".join(
        f"<dt>{escape(k)}</dt><dd>{escape(v)}</dd>" for k, v in rows) + "</dl>"


def hash_card(icon_name: str, title: str, value: str | None, rows: list[tuple[str, str]]) -> str:
    code = escape(value) if value else "Not available"
    return (f'<div class="hz-hash"><div class="hd">{icon(icon_name, 22)}<span>{escape(title)}</span></div>'
            f"<code>{code}</code>{kv(rows)}</div>")


def step(status: str, title: str, detail: str = "", timing: str = "") -> str:
    """status: ok / warn / bad / pending — symbol plus colour, never colour alone."""
    symbol = {"ok": "✓", "warn": "!", "bad": "✕"}.get(status, "–")
    tm = f'<span class="tm">{escape(timing)}</span>' if timing else ""
    return (f'<div class="hz-step"><span class="st {status}" aria-label="{status}">{symbol}</span>'
            f"<div><b>{escape(title)}</b><small>{escape(detail)}</small></div>{tm}</div>")


def empty(title: str, text: str, icon_name: str = "info") -> None:
    html(f'<div class="hz-empty"><div class="ic">{icon(icon_name, 28)}</div><div><b>{escape(title)}</b>'
         f"<p>{escape(text)}</p></div></div>")


def note(text_html: str, tone: str = "") -> None:
    """text_html must already be escaped/trusted markup."""
    html(f'<div class="hz-note {tone}">{icon("info" if tone != "bad" else "alert", 22)}<div>{text_html}</div></div>')


def disclaimer() -> None:
    note("<b>Research only — not a glaucoma diagnosis.</b> Results describe agreement between expert "
         "readers on public research datasets. They are not clinical accuracy and must not be used "
         "for patient care.")


def table(header: list[str], rows: list[list[str]], numeric: set[int] = frozenset(),
          highlight: set[int] = frozenset()) -> None:
    """Cells are escaped here; pass raw strings."""
    head = "".join(f'<th class="{"n" if i in numeric else ""}">{escape(h)}</th>'
                   for i, h in enumerate(header))
    body = []
    for r, row in enumerate(rows):
        cells = "".join(f'<td class="{"n" if i in numeric else ""}">{escape(str(c))}</td>'
                        for i, c in enumerate(row))
        body.append(f'<tr class="{"hl" if r in highlight else ""}">{cells}</tr>')
    html(f'<div class="hz-scroll"><table class="hz-table"><thead><tr>{head}</tr></thead>'
         f"<tbody>{''.join(body)}</tbody></table></div>")


def score_legend(scores: list[str]) -> None:
    """One shared legend for a row of small charts (swatch + text, never colour alone)."""
    from .theme import SCORE_COLORS, SCORE_LABELS
    html('<div class="hz-legend">' + "".join(
        f'<span><b style="display:inline-block;width:.8rem;height:.8rem;border-radius:3px;'
        f'background:{SCORE_COLORS[s]}"></b>{escape(SCORE_LABELS[s])}</span>' for s in scores) + "</div>")


def line_legend(items: list[tuple[str, str, str]]) -> str:
    """Legend of (label, colour, line style) — style is written out, never colour alone."""
    cls = {"solid": "", "dashed": "dash", "dotted": "dot"}
    return '<div class="hz-legend">' + "".join(
        f'<span style="color:{c}"><i class="{cls[s]}"></i><span style="color:#3B4A5E">'
        f"{escape(label)} · {s}</span></span>" for label, c, s in items) + "</div>"
