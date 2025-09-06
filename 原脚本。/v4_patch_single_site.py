# v4_patch_single_site.py  (零参数可跑：自动识别站点根目录与品牌)
# 作用：只在“不合格页面”上修复 Title / Description / 正文长度，
#      读取当前站的 keywords\*.txt 分配主关键词，
#      使用多模板+多槽位+稳定随机生成文案。
# 安全：合格页面不修改；已处理 insert_after 报错，保证在不完整 HTML 上也能落地。

import argparse, re, json, hashlib, random, sys
from pathlib import Path
from bs4 import BeautifulSoup

# ===== 可调阈值 =====
TARGET_TITLE = (45, 60)     # Title 目标长度
TARGET_DESC  = (130, 155)   # Description 目标长度
MIN_BODY     = 200          # 正文最小长度

# ===== 槽位词池（可按需增减）=====
STYLES = ["modern","vintage","minimal","urban","cinematic","natural","studio","retro"]
MOODS  = ["elegant","playful","moody","romantic","calm","bold","warm","cool"]
LIGHTS = ["soft lighting","golden-hour glow","window light","neon lights","backlight","overcast"]
COMPS  = ["close-up","rule-of-thirds","symmetry","leading lines","wide shot"]
WEARS  = ["casual","streetwear","office","evening dress","sporty","retro"]
BACKS  = ["urban backdrop","nature scene","indoor studio","minimal set","bedroom scene"]

# ===== 工具 =====
def _rng(seed: str):
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return random.Random(int(h[:8], 16))

def _facets(r):
    return dict(style=r.choice(STYLES), mood=r.choice(MOODS), light=r.choice(LIGHTS),
                comp=r.choice(COMPS), wear=r.choice(WEARS), back=r.choice(BACKS))

def _clamp(s: str, mx: int):
    if len(s) <= mx: return s
    cut = s[:mx].rsplit(" ", 1)[0]
    return cut if len(cut) >= int(mx*0.8) else s[:mx]

def _pad_to(s: str, mn: int, r, pads: list):
    t = s
    while len(t) < mn and pads:
        t += " — " + r.choice(pads); pads.pop(0)
    return t

def _read_lines(p: Path):
    if not p.exists(): return []
    txt = p.read_text(encoding="utf-8", errors="ignore")
    return [x.strip() for x in txt.splitlines() if x.strip()]

def _site_root_auto():
    """
    自动识别站点根目录：优先脚本所在目录；否则从当前工作目录往上找
    以是否存在 keywords/、sitemap.xml、index.html 为线索
    """
    candidates = [Path(__file__).resolve().parent, Path.cwd().resolve()]
    tried = set()
    for base in candidates:
        cur = base
        for _ in range(4):  # 最多向上4层
            if cur in tried: break
            tried.add(cur)
            if (cur/"keywords").exists() or (cur/"sitemap.xml").exists() or (cur/"index.html").exists():
                return cur
            cur = cur.parent
    # 实在找不到就用脚本目录
    return Path(__file__).resolve().parent

# ===== 关键词池（按目录名.txt；兜底 all.txt；唯一分配并稳定保存）=====
def _pick_pool_for(rel_dir: str, kw_dir: Path):
    parts = [p.lower() for p in Path(rel_dir).parts if p not in (".","")]
    for name in reversed(parts):  # 从最内层目录开始匹配
        f = kw_dir / f"{name}.txt"
        if f.exists():
            return _read_lines(f)
    return _read_lines(kw_dir / "all.txt")

def _load_used(kw_dir: Path):
    used_path = kw_dir / "used_keywords.json"
    if used_path.exists():
        return json.loads(used_path.read_text(encoding="utf-8"))
    return {}

def _save_used(kw_dir: Path, used: dict):
    (kw_dir / "used_keywords.json").write_text(
        json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def assign_primary_kw(root_dir: Path, abs_filepath: Path):
    """
    给页面分配一个主关键词（尽量唯一，稳定随机），记录到 keywords/used_keywords.json
    """
    kw_dir = root_dir / "keywords"
    kw_dir.mkdir(exist_ok=True)
    used = _load_used(kw_dir)

    site_key = str(root_dir.resolve())
    used.setdefault(site_key, {"map": {}, "used_set": []})

    rel_path = str(abs_filepath.resolve().relative_to(root_dir.resolve()))
    rel_dir  = str(Path(rel_path).parent)

    if rel_path in used[site_key]["map"]:
        return used[site_key]["map"][rel_path]

    pool = _pick_pool_for(rel_dir, kw_dir)
    if not pool:
        miss = root_dir / "logs" / "kw_miss.txt"
        miss.parent.mkdir(parents=True, exist_ok=True)
        miss.open("a", encoding="utf-8").write(rel_path + "\n")
        return None

    r = _rng("kw::"+rel_path)
    start = r.randrange(0, len(pool))
    used_set = set(used[site_key]["used_set"])

    pick = None
    for i in range(len(pool)):
        kw = pool[(start + i) % len(pool)]
        if kw not in used_set:
            pick = kw; break
    if pick is None:  # 词不够：允许复用
        pick = pool[start % len(pool)]

    used[site_key]["map"][rel_path] = pick
    used[site_key]["used_set"].append(pick)
    _save_used(kw_dir, used)
    return pick

def _infer_kw(soup: BeautifulSoup, filepath: Path):
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    return filepath.stem.replace("_"," ").replace("-"," ").strip()

# ===== DOM 安全辅助（修复 insert_after 报错的关键）=====
def _ensure_dom(soup: BeautifulSoup):
    """确保文档存在 <html><head><body> 并返回 (head, body)。"""
    if not soup.html:
        soup.append(soup.new_tag("html"))
    if not soup.head:
        soup.html.insert(0, soup.new_tag("head"))
    if not soup.body:
        soup.html.append(soup.new_tag("body"))
    return soup.head, soup.body

def _safe_insert_paragraph(soup: BeautifulSoup, paragraph_text: str):
    """优先插在 <h1> 或首个 <img> 之后；都没有就追加到 <body> 末尾。"""
    p = soup.new_tag("p")
    p.string = paragraph_text
    h1 = soup.find("h1")
    if h1:
        h1.insert_after(p)         # h1 一定是 Tag
        return
    img = soup.find("img")
    if img:
        img.insert_after(p)        # img 也是 Tag
        return
    # 都没有就 append 到 <body> 末尾（保证 body 存在）
    _, body = _ensure_dom(soup)
    body.append(p)

# ===== 文案生成（多模板+多槽位+长度硬控）=====
def gen_title(keyword: str, brand: str, seed: str):
    r = _rng("t::"+seed); f = _facets(r)
    cands = [
        f"{keyword} {f['style']} portraits | {brand}",
        f"{keyword} gallery — {f['mood']} tone | {brand}",
        f"{keyword} photos, {f['light']} | {brand}",
        f"High-quality {keyword} images — {f['comp']} | {brand}",
        f"{keyword} {f['mood']} lookbook | {brand}",
    ]
    t = r.choice(cands)
    if len(t) < TARGET_TITLE[0]:
        t += f" — {f['mood']} {f['style']}"
    return _clamp(t, TARGET_TITLE[1])

def gen_desc(keyword: str, seed: str):
    r = _rng("d::"+seed); f = _facets(r)
    base = (f"Explore {keyword} in {f['style']} style with {f['mood']} vibe, "
            f"{f['light']}, and {f['comp']} framing. Curated images on a fast, clean page.")
    pads = [f"{f['wear']} looks and {f['back']}",
            "Simple navigation helps discovery",
            "Mobile-friendly layout for smooth viewing",
            "Short notes keep context clear",
            "Clean typography keeps focus on the visuals"]
    s = _pad_to(base, TARGET_DESC[0], r, pads)
    return _clamp(s, TARGET_DESC[1])

def gen_para(keyword: str, seed: str):
    r = _rng("p::"+seed); f = _facets(r)
    s = (f"This set explores {keyword} through {f['style']} aesthetics and {f['mood']} tone under {f['light']}. "
         f"Compositions use {f['comp']} with {f['back']}, keeping focus clear and tidy. "
         f"Details like {f['wear']} styling and balanced colors make browsing easy.")
    if len(s) < MIN_BODY:
        s += " Pages load quickly and related links help deeper viewing."
    return _clamp(s, 300)

# ===== 只修不合格页面 =====
def enhance_if_needed(html_text: str, filepath: Path, brand: str, root_dir: Path):
    soup = BeautifulSoup(html_text, "html.parser")

    # 当前页面状态
    title = (soup.title.string if soup.title and soup.title.string else "")
    mdesc = soup.find("meta", {"name":"description"})
    desc  = (mdesc.get("content") if mdesc else "") or ""
    body_len = len(re.sub(r"\s+"," ", soup.get_text(" ", strip=True)))

    need = (len(title) < 30) or (len(desc) < 110) or (body_len < MIN_BODY)
    if not need:
        return html_text, False  # 合格页不动

    # 关键词：目录词池优先，缺了再用 H1/文件名
    kw = assign_primary_kw(root_dir, filepath) or _infer_kw(soup, filepath)
    seed = str(filepath)

    new_title = gen_title(kw, brand, seed)
    new_desc  = gen_desc(kw, seed)
    new_para  = gen_para(kw, seed)

    # 确保 DOM 结构完整
    head, body = _ensure_dom(soup)

    # 写入 <title>
    if not soup.title:
        t = soup.new_tag("title")
        head.append(t)
    soup.title.string = new_title

    # 写入 <meta name="description">
    mdesc = soup.find("meta", {"name": "description"})
    if not mdesc:
        mdesc = soup.new_tag("meta", attrs={"name": "description", "content": new_desc})
        head.append(mdesc)
    else:
        mdesc["content"] = new_desc

    # 正文不足才补段落（安全插入）
    if body_len < MIN_BODY:
        _safe_insert_paragraph(soup, new_para)

    return str(soup), True

# ===== 主函数（支持零参数） =====
def main():
    ap = argparse.ArgumentParser(description="v4 单站补丁（零参数可跑）")
    ap.add_argument("--root", help="站点根目录，不填则自动识别")
    ap.add_argument("--brand", help="品牌/站名，不填则用根目录名")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else _site_root_auto()
    brand = args.brand if args.brand else root.name

    if not root.exists():
        print(f"[FATAL] 根目录不存在：{root}")
        sys.exit(2)

    (root/"logs").mkdir(exist_ok=True)
    html_files = list(root.rglob("*.html"))
    changed = 0

    for i, fp in enumerate(html_files, 1):
        try:
            html = fp.read_text(encoding="utf-8")
        except Exception:
            html = fp.read_text(errors="ignore")

        new_html, ok = enhance_if_needed(html, fp, brand, root)
        if ok:
            fp.write_text(new_html, encoding="utf-8")
            changed += 1

        if i % 500 == 0:
            print(f"[PROGRESS] {i}/{len(html_files)} processed; changed={changed}")

    print(f"[DONE] root={root} ; total={len(html_files)} ; modified={changed}")

if __name__ == "__main__":
    main()
