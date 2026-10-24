"""Small inline SVG icon set (stroke icons, 24×24 grid) for HTML components."""
from __future__ import annotations

_PATHS = {
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/>'
                '<path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/>'
             '<path d="m21 16-5-5-9 9"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.5-3.6 3.2-5.5 6.5-5.5s6 1.9 6.5 5.5"/>'
             '<circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.6c2.6.2 4.4 1.9 4.9 5.4"/>',
    "trend": '<path d="m3 17 6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "shield": '<path d="M12 3 4 6v6c0 4.5 3.4 8.2 8 9 4.6-.8 8-4.5 8-9V6z"/>',
    "shield_check": '<path d="M12 3 4 6v6c0 4.5 3.4 8.2 8 9 4.6-.8 8-4.5 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    "alert": '<path d="M12 3 2 20h20z"/><path d="M12 10v4"/><path d="M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "file": '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>'
            '<path d="M8 13h8"/><path d="M8 17h5"/>',
    "chart": '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "download": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 21h16"/>',
    "split": '<circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="18" r="2.5"/><circle cx="12" cy="5" r="2.5"/>'
             '<path d="M12 7.5V12l-6 3.5"/><path d="m12 12 6 3.5"/>',
    "fingerprint": '<path d="M12 11v3a8 8 0 0 1-2 5"/><path d="M8 9a4 4 0 0 1 8 0v4"/>'
                   '<path d="M5 11a7 7 0 0 1 14 0v2a12 12 0 0 1-1 5"/>',
    "interval": '<path d="M4 4v16"/><path d="M20 4v16"/><path d="M4 12h16"/><circle cx="12" cy="12" r="2"/>',
}


def icon(name: str, size: int = 24, stroke: str = "currentColor") -> str:
    body = _PATHS.get(name, _PATHS["info"])
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{stroke}" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f"{body}</svg>")


LOGO = (
    '<svg width="44" height="44" viewBox="0 0 48 48" aria-hidden="true">'
    '<circle cx="24" cy="24" r="21" fill="none" stroke="#1D6FD8" stroke-width="3"/>'
    '<path d="M6 24c4-7 10.5-11 18-11s14 4 18 11c-4 7-10.5 11-18 11S10 31 6 24z" fill="#E8F1FC" '
    'stroke="#0B5CAD" stroke-width="2.4"/>'
    '<circle cx="24" cy="24" r="8" fill="#0B5CAD"/><circle cx="24" cy="24" r="4" fill="#0A1A2F"/>'
    '<circle cx="21.5" cy="21.5" r="1.8" fill="#fff"/></svg>'
)
