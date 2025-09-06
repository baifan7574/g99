# -*- coding: utf-8 -*-
"""
site_enhance_all.py
一体化补丁：Slogan 随机化 + 分类页差异化描述 + 结构差异化（专题页/相关推荐/版式A/B/C）
丢根目录执行：python site_enhance_all.py

安全特性：
- 每个被改的 HTML 都会生成 .bak 备份（第一次改动时）
- 幂等标记：data-nb-*，重复运行不会重复插入
- 找不到安全插入点会跳过，不强插

你可以在同目录放两个可选配置文件：
- slogans.txt（每行一句）
- category_desc_templates.txt（spintax/模板句式，见下文）
- site_structure_config.json（可选，覆盖默认分类目录/专题等）
"""
import os, re, json, random, math
from pathlib import Path

ROOT = Path(".")
HTML_EXTS = (".html", ".htm")

# ====== 1) 配置与默认数据 ======
CFG_PATH = ROOT / "site_structure_config.json"
SLOGANS_PATH = ROOT / "slogans.txt"
CAT_TMPL_PATH = ROOT / "category_desc_templates.txt"

DEFAULT_CFG = {
    "variant": "auto",  # auto | A | B | C
    "category_dirs": ["bedroom","dark","soft","office","uniform","fitness","mirror","shower","luxury"],
    "collections": [
        {"slug": "morning-light", "title": "Morning Light", "include": ["morning","sun","window","soft"]},
        {"slug": "cozy-bedroom", "title": "Cozy Bedroom", "include": ["blanket","cozy","warm","pillow"]},
        {"slug": "soft-portraits", "title": "Soft Portraits", "include": ["soft","bokeh","gentle","pastel"]},
        {"slug": "moody-tones", "title": "Moody Tones", "include": ["dark","shadow","night","lamp"]},
        {"slug": "natural-look", "title": "Natural Look", "include": ["natural","casual","smile","clean"]}
    ],
    "max_related_thumbs": 8,
    "min_related_thumbs": 5,
    "dry_run": False
}

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

def load_cfg():
    if CFG_PATH.exists():
        try:
            return {**DEFAULT_CFG, **json.loads(CFG_PATH.read_text("utf-8"))}
        except Exception:
            return DEFAULT_CFG
    return DEFAULT_CFG

CFG = load_cfg()
DRY = CFG.get("dry_run", False)

def safe_write(p: Path, new_text: str):
    if DRY:
        print("[DRY] would write:", p)
        return
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        try:
            bak.write_text(p.read_text("utf-8", errors="ignore"), "utf-8")
        except Exception:
            pass
    p.write_text(new_text, "utf-8")

# ====== 2) 首页 Slogan 随机化 ======
def load_slogans():
    if SLOGANS_PATH.exists():
        lines = [x.strip() for x in SLOGANS_PATH.read_text("utf-8", errors="ignore").splitlines() if x.strip()]
        return lines or [
            "Images that whisper stories.",
            "A quiet gallery of light and mood.",
            "Elegance in subtle frames.",
            "Where portraits meet emotion.",
            "Gentle tones, honest moments."
        ]
    return [
        "Images that whisper stories.",
        "A quiet gallery of light and mood.",
        "Elegance in subtle frames.",
        "Where portraits meet emotion.",
        "Gentle tones, honest moments."
    ]

def patch_home_slogan():
    slogans = load_slogans()
    idx = ROOT / "index.html"
    if not idx.exists(): 
        print("[slogan] skip (no index.html)")
        return
    html = idx.read_text("utf-8", errors="ignore")
    if MARK["slogan"] in html:
        print("[slogan] exists ->", idx)
        return
    s = random.choice(slogans)
    # 常见位置：h2/subtitle/hero 区域；策略：在第一个 <h1> 后插入一行副标题
    m = re.search(r"<h1[^>]*>.*?</h1>", html, flags=re.I|re.S)
    if not m:
        m = re.search(r"<body[^>]*>", html, flags=re.I)
        if not m:
            print("[slogan] no safe insert point ->", idx); return
    insert_at = m.end()   # 上面已保证 m 存在
    block = f'\n<p class="nb-sub" {MARK["slogan"]}="1" style="opacity:.9;margin:6px 0 12px">{s}</p>\n'
    out = html[:insert_at] + block + html[insert_at:]
    safe_write(idx, out)
    print("[slogan] ok ->", idx)

# ====== 3) 分类页差异化描述 ======
def load_cat_templates():
    # 支持 spintax：{A|B} 任选其一；{a|b|c}
    base = [
        "Explore {bedroom|gallery|collection} portraits with {soft|gentle|subtle} lighting and {natural|casual} moods. This page curates {intimate|quiet|serene} moments and {elegant|clean} frames.",
        "Browse {bedroom|portrait} images featuring {morning light|cozy atmosphere|warm tones} and {relaxed|honest} expressions. A {handpicked|curated} set for {inspiration|reference}.",
        "Discover {bedroom-themed|indoor} portraits focused on {texture|light|color} and {emotion|presence}. Crafted for viewers who enjoy {subtle|minimal} aesthetics."
    ]
    if CAT_TMPL_PATH.exists():
        lines = [x.strip() for x in CAT_TMPL_PATH.read_text("utf-8", errors="ignore").splitlines() if x.strip()]
        if lines: base = lines
    return base

def spintax(s: str):
    # 简单 spintax 实现
    while True:
        m = re.search(r"\{([^{}]+)\}", s)
        if not m: break
        choices = m.group(1).split("|")
        s = s[:m.start()] + random.choice(choices) + s[m.end():]
    return s

def is_category_page(p: Path):
    parts = p.relative_to(ROOT).parts
    if len(parts) < 2: return False
    cat = parts[-2].lower()
    if cat not in [c.lower() for c in CFG["category_dirs"]]: return False
    name = p.name.lower()
    return name.startswith("page") or name == "index.html"

def insert_cat_desc(p: Path):
    html = p.read_text("utf-8", errors="ignore")
    if MARK["catdesc"] in html:
        return False, "exists"
    # 1) 尝试替换你原来的那句固定描述（Browse bedroom images...）
    repl = False
    newp = f'<p {MARK["catdesc"]}="1">{spintax(random.choice(load_cat_templates()))}</p>'
    # 替换策略：找到 h1 后面的第一个 <p>，如果它很短且包含 browse/collection 等词，替换为新描述；否则插入到 h1 后
    h1 = re.search(r"<h1[^>]*>.*?</h1>", html, flags=re.I|re.S)
    if h1:
        after_h1 = html[h1.end():]
        mp = re.search(r"<p[^>]*>.*?</p>", after_h1, flags=re.I|re.S)
        if mp:
            seg = after_h1[mp.start():mp.end()]
            if len(seg) < 220 and re.search(r"browse|gallery|collection|images", seg, flags=re.I):
                out = html[:h1.end()] + after_h1[:mp.start()] + newp + after_h1[mp.end():]
                safe_write(p, out); return True, "replaced"
        # 插入到 h1 后
        out = html[:h1.end()] + "\n" + newp + "\n" + html[h1.end():]
        safe_write(p, out); return True, "inserted"
    # 如果没有 h1，就尝试插在 <main> 或 <body> 后
    m = re.search(r"<main[^>]*>", html, flags=re.I)
    if not m: m = re.search(r"<body[^>]*>", html, flags=re.I)
    if not m: return False, "no-insert-point"
    out = html[:m.end()] + "\n" + newp + "\n" + html[m.end():]
    safe_write(p, out); return True, "inserted"

def patch_category_descriptions():
    touched = 0; total = 0
    for root, _, files in os.walk(ROOT):
        for f in files:
            if not f.lower().endswith(HTML_EXTS): continue
            p = Path(root) / f
            if is_category_page(p):
                total += 1
                ok, msg = insert_cat_desc(p)
                if ok: touched += 1
                print(f"[catdesc] {msg} -> {p}")
    print(f"[catdesc] done: {touched}/{total}")

# ====== 4) 结构差异化（专题页/相关推荐/三版式） ======
def pick_variant():
    v = CFG.get("variant","auto")
    if v in ("A","B","C"): return v
    return random.choice(["A","B","C"])

def is_image_page(p: Path):
    parts = p.relative_to(ROOT).parts
    if len(parts) < 2: return False
    cat = parts[-2].lower()
    if cat not in [c.lower() for c in CFG["category_dirs"]]: return False
    n = p.name.lower()
    return (n.endswith(".html") or n.endswith(".htm")) and not n.startswith("page") and n != "index.html"

def find_first_img_src(html: str):
    m = re.search(r'<img[^>]+src="([^"]+)"', html, flags=re.I)
    return m.group(1) if m else ""

def list_image_pages(cat: str):
    catdir = ROOT / cat
    pages = []
    if not catdir.exists(): return pages
    for p in sorted(catdir.rglob("*.html")):
        if is_image_page(p):
            pages.append(p)
    return pages

def build_related_block(cat: str, exclude_name: str):
    pages = list_image_pages(cat)
    pages = [p for p in pages if p.name != exclude_name]
    random.shuffle(pages)
    kmin = CFG["min_related_thumbs"]; kmax = CFG["max_related_thumbs"]
    k = min(max(kmin, 1), kmax, len(pages))
    if k == 0: return ""
    thumbs = []
    for p in pages[:k]:
        html = p.read_text("utf-8", errors="ignore")
        src = find_first_img_src(html)
        href = "/" + p.relative_to(ROOT).as_posix()
        thumbs.append(f'<a class="nb-thumb" href="{href}"><img loading="lazy" src="{src}" alt=""></a>')
    block = f"""
{CSS_BLOCK}
<div class="nb-box" {MARK["related"]}="1">
  <div class="nb-h2">You may also like</div>
  <div class="nb-grid">{''.join(thumbs)}</div>
</div>
""".strip()
    return block

def insert_block(html: str, block: str, pos="below"):
    if not block: return html, False
    def before_grid(s):
        m = re.search(r"<img[^>]+src=", s, flags=re.I)
        return m.start() if m else None
    def after_grid(s):
        last = None
        for m in re.finditer(r"<img[^>]+src=", s, flags=re.I):
            last = m
        return last.end() if last else None
    def find_after(tag, s):
        m = re.search(fr"<{tag}[^>]*>", s, flags=re.I)
        return m.end() if m else None
    if pos == "above":
        idx = before_grid(html) or find_after("main", html) or find_after("body", html)
    elif pos == "sidebar":
        idx = find_after("body", html)
        if idx is not None:
            block = block.replace('class="nb-box"', 'class="nb-box nb-sidebar"')
    else:  # below
        idx = after_grid(html) or find_after("main", html) or find_after("body", html)
    if idx is None: return html, False
    out = html[:idx] + "\n" + block + "\n" + html[idx:]
    return out, True

def build_collections_links():
    links = []
    for c in CFG["collections"]:
        links.append(f'<span class="nb-tag"><a href="/tags/{c["slug"]}.html">{c["title"]}</a></span>')
    return f"""
{CSS_BLOCK}
<div class="nb-box" {MARK["collections"]}="1">
  <div class="nb-h2">Top Collections</div>
  <div class="nb-tags">{''.join(links)}</div>
</div>
""".strip()

def ensure_tags_pages():
    tags_dir = ROOT / "tags"
    if not DRY:
        tags_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for c in CFG["collections"]:
        slug, title, inc = c["slug"], c["title"], [x.lower() for x in c["include"]]
        matches = []
        for cat in CFG["category_dirs"]:
            for p in list_image_pages(cat):
                name = p.name.lower()
                if any(k in name for k in inc):
                    html = p.read_text("utf-8", errors="ignore")
                    src = find_first_img_src(html)
                    href = "/" + p.relative_to(ROOT).as_posix()
                    matches.append((href, src))
        per = 30
        pages = max(1, math.ceil(len(matches)/per))
        for i in range(pages):
            cur = matches[i*per:(i+1)*per]
            thumbs = "".join([f'<a class="nb-thumb" href="{h}"><img loading="lazy" src="{s}" alt=""></a>' for h,s in cur])
            nav = []
            if i+1 < pages: nav.append(f'<a href="/tags/{slug}_{i+2}.html">Next</a>')
            content = f"""<!doctype html><html><head><meta charset="utf-8"><title>{title} Collection</title>{CSS_BLOCK}</head>
<body class="nb-wrap">
  <nav class="nb-breadcrumb"><a href="/">Home</a> › <span aria-current="page">{title}</span></nav>
  <h1>{title} Collection</h1>
  <div class="nb-grid">{thumbs}</div>
  <div class="nb-btm">{' | '.join(nav)} · <a href="/">Home</a></div>
</body></html>"""
            out = tags_dir / (f"{slug}.html" if i==0 else f"{slug}_{i+1}.html")
            if DRY: print("[DRY] tags ->", out, "items:", len(cur))
            else: out.write_text(content, "utf-8")
        total += len(matches)
        print(f"[tags] {slug}: {len(matches)} items")
    print(f"[tags] total items: {total}")

def patch_category_page(p: Path, variant: str):
    html = p.read_text("utf-8", errors="ignore")
    changed = False
    if MARK["collections"] not in html:
        blk = build_collections_links()
        pos = {"A":"above","B":"sidebar","C":"below"}[variant]
        html2, ok = insert_block(html, blk, pos=pos)
        if ok: html, changed = html2, True
    if changed:
        html = html.replace("<body", f'<body {MARK["variant"]}="{variant}"', 1)
        safe_write(p, html)
        print("[category]", variant, "->", p)
    else:
        print("[category] skip ->", p)

def patch_image_page(p: Path, variant: str):
    parts = p.relative_to(ROOT).parts
    cat = parts[-2]
    html = p.read_text("utf-8", errors="ignore")
    if MARK["related"] in html:
        print("[image] exists ->", p); return
    blk = build_related_block(cat, exclude_name=p.name)
    if not blk:
        print("[image] no-related ->", p); return
    pos = {"A":"below","B":"sidebar","C":"below"}[variant]
    html2, ok = insert_block(html, blk, pos=pos)
    if ok:
        html = html2.replace("<body", f'<body {MARK["variant"]}="{variant}"', 1)
        safe_write(p, html)
        print("[image]", variant, "->", p)
    else:
        print("[image] no-insert-point ->", p)

def run_structure_patch():
    variant = pick_variant()
    print("Variant:", variant)
    ensure_tags_pages()
    for root, _, files in os.walk(ROOT):
        for f in files:
            if not f.lower().endswith(HTML_EXTS): continue
            p = Path(root) / f
            if is_category_page(p):
                patch_category_page(p, variant)
            elif is_image_page(p):
                patch_image_page(p, variant)

def main():
    patch_home_slogan()
    patch_category_descriptions()
    run_structure_patch()
    print("\n✅ enhance done.")

if __name__ == "__main__":
    main()
