# -*- coding: utf-8 -*-
"""
patch_homepage.py  — 主页注入：canonical / ads(可选) / schema(可选)
- 兼容 config.json 或 config_*.json，ads_code 可为字符串或列表
- 当没有广告代码时，安全跳过，不报错
"""
import json, re
from pathlib import Path

ROOT = Path(".")
INDEX = ROOT / "index.html"

CONF_CANDIDATES = [
    ROOT / "config.json",
    ROOT / "config_uniform.json",
    ROOT / "config_office.json",
    ROOT / "config_dark.json",
]

def load_config():
    for p in CONF_CANDIDATES:
        if p.exists():
            try:
                return json.loads(p.read_text("utf-8")), p.name
            except Exception:
                pass
    return {}, "(none)"

def upsert_in_head(html: str, snippet: str):
    if not snippet.strip():
        return html
    head_close = re.search(r"</head\s*>", html, flags=re.I)
    if not head_close:
        return snippet + html
    return html[:head_close.start()] + snippet + "\n" + html[head_close.start():]

def main():
    if not INDEX.exists():
        print("[homepage] index.html not found, skip")
        return

    cfg, cfg_name = load_config()
    domain = (cfg.get("domain") or "").strip().rstrip("/")
    enable_ads = bool(cfg.get("enable_ads", False))
    ads_code_raw = cfg.get("ads_code", "")

    # —— 安全解析广告代码（字符串/列表/空值）
    if isinstance(ads_code_raw, list):
        ads_code = ads_code_raw[0].strip() if ads_code_raw else ""
    else:
        ads_code = (ads_code_raw or "").strip()

    html = INDEX.read_text("utf-8", errors="ignore")

    # 1) canonical
    if domain:
        canonical = f'{domain}/index.html'
        if not re.search(r'rel=["\']canonical["\']', html, flags=re.I):
            html = upsert_in_head(html, f'<link rel="canonical" href="{canonical}">')
            print("[homepage] canonical injected")
        else:
            print("[homepage] canonical exists")
    else:
        print("[homepage] no domain in", cfg_name, "-> skip canonical")

    # 2) schema（可选）
    schema_snippet = cfg.get("homepage_schema")
    if schema_snippet and not re.search(r'<script[^>]+application/ld\+json', html, flags=re.I):
        html = upsert_in_head(
            html,
            schema_snippet if schema_snippet.strip().startswith("<script")
            else f'<script type="application/ld+json">{schema_snippet}</script>'
        )
        print("[homepage] schema injected")
    else:
        print("[homepage] schema skipped")

    # 3) ads（可选）：仅当开启且有代码时注入
    if enable_ads and ads_code:
        m = re.search(r"</body\s*>", html, flags=re.I)
        if m:
            html = html[:m.start()] + ads_code + "\n" + html[m.start():]
        else:
            html += "\n" + ads_code + "\n"
        print("[homepage] ads injected")
    else:
        print("[homepage] ads skipped (enable_ads=%s, code=%s)" % (enable_ads, "yes" if bool(ads_code) else "no"))

    INDEX.write_text(html, "utf-8")
    print("[homepage] done. config:", cfg_name)

if __name__ == "__main__":
    main()
