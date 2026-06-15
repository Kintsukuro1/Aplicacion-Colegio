import re
from pathlib import Path

pat = re.compile(r"^\s*\{% include 'profesor/_profesor_hero\.html'.*%\}\s*$")
root = Path(__file__).resolve().parents[1] / "frontend_django/templates"
for p in root.rglob("*.html"):
    if p.name in ("_profesor_hero.html", "_profesor_hero_from_ctx.html"):
        continue
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    new = [ln for ln in lines if not pat.match(ln)]
    if len(new) != len(lines):
        p.write_text("\n".join(new) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
        print(p)
