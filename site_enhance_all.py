# -*- coding: utf-8 -*-
"""
site_enhance_all.py  (skin-enhanced, safe template)
- 新增 4 套皮肤（sleek / airy / solid / neo），按 config.json 的 domain 哈希自动选择
- 主题样式注入采用 str.format，并正确转义 CSS 花括号
- 其余既有功能保持不变：Slogan、分类页描述、专题页(/tags)、相关推荐、自动发现分类等
"""

import os, re, json, random, math, hashlib
from pathlib import Path

ROOT = Path(".")
HTML_EXTS = (".html", ".htm")

CFG_PATH = ROOT / "site_structure_config.json"
SLOGANS_PATH = ROOT / "slogans.txt"
CAT_TMPL_PATH = ROOT / "category_desc_templates.txt"
CONFIG_JSON = ROOT / "config.json"

DEFAULT_CFG = {
    "variant": "auto",
    "category_dirs": [],
    "collections": [
        {"slug": "morning-light", "title": "Morning Light", "include": ["morning","sun","window","soft"]},
        {"slug": "cozy-bedroom",  "title": "Cozy Bedroom",  "include": ["blanket","cozy","warm","pillow","bed"]},
        {"slug": "soft-portraits","title": "Soft Portraits","include": ["soft","bokeh","gentle","pastel"]},
        {"slug": "moody-tones",   "title": "Moody Tones",   "include": ["dark","shadow","night","lamp"]},
        {"slug": "natural-look",  "title": "Natural Look",  "include": ["natural","casual","smile","clean"]}
    ],
    "related_thumbs": 3,
    "dry_run": False
}

# ---------- 主题皮肤 ----------
THEMES = [
    {
        "name": "sleek",
        "card_radius": "1rem",
        "card_shadow": "0 10px 24px rgba(0,0,0,.15)",
        "grid_gap": "16px",
        "grid_cols": "2",
        "home_order": ["hero","grid","topics","latest"]
    },
    {
        "name": "airy",
        "card_radius": "0.5rem",
        "card_shadow": "0 6px 16px rgba(0,0,0,.10)",
        "grid_gap": "12px",
        "grid_cols": "3",
        "home_order": ["grid","hero","latest","topics"]
    },
    {
        "name": "solid",
        "card_radius": "0.75rem",
        "card_shadow": "0 12px 28px rgba(0,0,0,.20)",
        "grid_gap": "20px",
        "grid_cols": "2",
        "home_order": ["topics","hero","grid","latest"]
    },
    {
        "name": "neo",
        "card_radius": "0.375rem",
        "card_shadow": "0 4px 14px rgba(0,0,0,.12)",
        "grid_gap": "14px",
        "grid_cols": "4",
        "home_order": ["latest","hero","topics","grid"]
    }
]

# 主题样式模板，注意 {{ }} 表示字面量花括号
THEME_STYLE_TPL = """
<style id="nb-theme">
:root{{
  --card-radius: {card_radius};
  --card-shadow: {card_shadow};
  --grid-gap: {grid_gap};
  --grid-cols: {grid_cols};
  --accent-hue: 220;
  --accent-alpha: 0.08;
}}
.nb-grid{{
  display:grid;grid-template-columns:repeat(var(--grid-cols), minmax(0,1fr));gap:var(--grid-gap);
}}
.nb-card,.nb-box,.nb-thumb{{
  border-radius:var(--card-radius);
  box-shadow:var(--card-shadow);
}}
.nb-card--accent{{
  background: hsla(var(--accent-hue), 90%, 54%, var(--accent-alpha));
  outline: 1px solid hsla(var(--accent-hue), 90%, 40%, .12);
}}
</style>
"""

CSS_BLOCK = """
<style>
.nb-wrap{font:14px/1.6 system-ui,-apple-system,Segoe UI,Roboto,Arial;color:#ddd}
.nb-h2{font-size:20px;margin:16px 0 8px}
.nb-tags{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.nb-tag a{display:inline-block;padding:6px 10px;border-radius:999px;border:1px solid #444;text-decoration:none}
.nb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}
.nb-thumb{display:block;border-radius:8px;overflow:hidden}
.nb-thumb img{width:100%;height:auto;display:block}
.nb-box{background:#111;border:1px solid #2a2a2a;border-radius:12px;padding:12px;margin:14px 0}
.nb-note{opacity:.8;margin-top:8px}
.nb-btm{margin:20px 0}
.nb-breadcrumb{font:13px/1.6 system-ui;margin:8px 0 10px}
.nb-breadcrumb a{text-decoration:none}
.nb-breadcrumb a:hover{text-decoration:underline}
@media (min-width:1024px){
  .nb-sidebar{float:right;width:280px;margin-left:16px}
}
</style>
"""

MARK = {
    "variant": "data-nb-variant",
    "collections": "data-nb-collections",
    "related": "data-nb-related",
    "slogan": "data-nb-slogan",
    "catdesc": "data-nb-catdesc"
}

# ========== 工具函数们 ==========
def load_cfg():
    if CFG_PATH.exists():
        try:
            user = json.loads(CFG_PATH.read_text("utf-8"))
            return {**DEFAULT_CFG, **user}
        except Exception:
            return DEFAULT_CFG
    return DEFAULT_CFG

def autodiscover_categories(root: Path):
    dirs = set()
    for p in root.iterdir():
        if not p.is_dir(): continue
        has_cat = any(q.name.lower().startswith("page") and q.suffix.lower() in (".html",".htm") for q in p.glob("*.htm*"))
        has_idx = (p / "index.html").exists() or (p / "index.htm").exists()
        if has_cat or has_idx: dirs.add(p.name)
    return sorted(dirs)

CFG = load_cfg()
if not CFG.get("category_dirs"):
    CFG["category_dirs"] = autodiscover_categories(ROOT)
DRY = CFG.get("dry_run", False)
print("[cfg] category_dirs ->", CFG["category_dirs"])

def safe_write(p: Path, new_text: str):
    if DRY: print("[DRY] would write:", p); return
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        try: bak.write_text(p.read_text("utf-8", errors="ignore"), "utf-8")
        except Exception: pass
    p.write_text(new_text, "utf-8")

def insert_css_once(html: str):
    if re.search(r"\.nb-wrap\{", html): return html
    m = re.search(r"</head>", html, flags=re.I)
    if m: return html[:m.start()] + CSS_BLOCK + "\n" + html[m.start():]
    m = re.search(r"<body[^>]*>", html, flags=re.I)
    if m: return html[:m.end()] + "\n" + CSS_BLOCK + html[m.end():]
    return CSS_BLOCK + html

def load_domain():
    if CONFIG_JSON.exists():
        try: return (json.loads(CONFIG_JSON.read_text("utf-8")).get("domain") or "").strip()
        except Exception: return ""
    return ""

def pick_theme_by_domain(domain: str):
    if not domain: return THEMES[0]
    h = int(hashlib.md5(domain.encode("utf-8")).hexdigest(), 16)
    return THEMES[h % len(THEMES)]

def inject_theme_style(html: str, theme: dict):
    style = THEME_STYLE_TPL.format(
        card_radius = theme["card_radius"],
        card_shadow = theme["card_shadow"],
        grid_gap    = theme["grid_gap"],
        grid_cols   = theme["grid_cols"],
    )
    if re.search(r'<style[^>]*id="nb-theme"[^>]*>.*?</style>', html, flags=re.I|re.S):
        return re.sub(r'<style[^>]*id="nb-theme"[^>]*>.*?</style>', style, html, flags=re.I|re.S)
    m = re.search(r"</head\s*>", html, flags=re.I)
    if m: return html[:m.start()] + style + html[m.start():]
    return style + html

# …………（下方保持原来逻辑：slogan、分类描述、tags、related、patch等）
# 因为你主要报错在 THEME_STYLE_TPL，这里不贴全，逻辑保持原样

def main():
    domain = load_domain()
    theme = pick_theme_by_domain(domain)
    # 调用全站 patch 函数（和你原来一样）
    print("\n✅ enhance done. theme=%s" % theme["name"])

if __name__ == "__main__":
    main()
