#!/usr/bin/env python3
"""
Build the TASS book as a single PDF ebook.

    pip install markdown weasyprint
    python book/build_pdf.py            # → book/TASS-book.pdf

Assembles front matter + chapters 1-11 + appendices A-C from
book/chapters/, converts to HTML, applies print CSS (A4, page numbers,
chapter breaks), and renders with WeasyPrint.
"""

import datetime
import re
from pathlib import Path

import markdown
from weasyprint import HTML

BOOK = Path(__file__).resolve().parent
OUT = BOOK / "TASS-book.pdf"

CHAPTER_FILES = [
    "01-economics.md", "02-tokenizers.md", "03-format.md",
    "04-schema-compilation.md", "05-parsing.md", "06-file-format.md",
    "07-benchmarking.md", "08-crypto.md", "09-system-design.md",
    "10-case-studies.md", "11-beyond-llm.md",
    "appendix-a-api.md", "appendix-b-glossary.md", "appendix-c-use-cases.md",
]

CSS = """
@page {
    size: A4;
    margin: 22mm 18mm 20mm 18mm;
    @bottom-center { content: counter(page); font-family: Georgia, serif;
                     font-size: 9pt; color: #666; }
    @top-right { content: "Tokeniser-Aware Structured Shorthand";
                 font-family: Georgia, serif; font-size: 8pt; color: #999; }
}
@page :first { @top-right { content: none; } @bottom-center { content: none; } }

body { font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt;
       line-height: 1.55; color: #1a1a1a; }
h1 { page-break-before: always; font-size: 21pt; line-height: 1.25;
     border-bottom: 2px solid #1a1a1a; padding-bottom: 6pt; margin-top: 0; }
h1#cover-title { page-break-before: avoid; border: none; }
h2 { font-size: 14pt; margin-top: 18pt; color: #111; }
h3 { font-size: 11.5pt; margin-top: 14pt; }
p, li { text-align: justify; }
blockquote { margin: 10pt 14pt; padding: 6pt 12pt; border-left: 3px solid #888;
             color: #444; font-style: italic; background: #f7f7f5; }
code { font-family: 'DejaVu Sans Mono', Menlo, monospace; font-size: 8.6pt;
       background: #f2f2ef; padding: 0 2pt; border-radius: 2pt; }
pre { background: #f6f6f3; border: 0.5pt solid #ddd; border-radius: 3pt;
      padding: 8pt 10pt; font-size: 8.2pt; line-height: 1.4;
      white-space: pre-wrap; word-wrap: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
pre.mermaid-src { background: #eef3f8; border-color: #b8cbe0; }
pre.mermaid-src::before { content: "Architecture diagram (Mermaid source — renders on GitHub)";
      display: block; font-family: Georgia, serif; font-style: italic;
      font-size: 8.5pt; color: #456; margin-bottom: 6pt; }
table { border-collapse: collapse; width: 100%; margin: 10pt 0;
        font-size: 9pt; page-break-inside: avoid; }
th, td { border: 0.5pt solid #999; padding: 4pt 6pt; text-align: left; }
th { background: #ececea; }
hr { border: none; border-top: 0.5pt solid #bbb; margin: 14pt 0; }
a { color: #1a1a1a; text-decoration: none; }
.cover { text-align: center; padding-top: 70mm; page-break-after: always; }
.cover h1 { font-size: 30pt; border: none; }
.cover .subtitle { font-size: 14pt; font-style: italic; color: #333; margin-top: 8pt; }
.cover .meta { margin-top: 50mm; font-size: 10pt; color: #555; line-height: 1.8; }
.toc { page-break-after: always; }
"""

COVER = f"""
<div class="cover">
  <h1 id="cover-title">Tokeniser-Aware<br/>Structured Shorthand</h1>
  <div class="subtitle">The Engineering of Token-Efficient<br/>
       Machine-to-Machine LLM Pipelines</div>
  <div class="meta">
     Companion book to the TASS protocol<br/>
     github.com/suyash333/TASS-protocol<br/>
     White paper DOI: 10.5281/zenodo.20403219<br/><br/>
     Built {datetime.date.today().isoformat()} · MIT License
  </div>
</div>
"""


def preprocess(md_text: str) -> str:
    """Adapt repo-flavoured markdown for a standalone PDF."""
    # Repo-relative links → plain text (the PDF has no filesystem)
    md_text = re.sub(r"\[([^\]]+)\]\((?!https?://)[^)]+\)", r"\1", md_text)
    # Mermaid fences → tagged pre blocks (styled as diagram source)
    md_text = re.sub(r"```mermaid\n(.*?)```",
                     lambda m: "<pre class='mermaid-src'><code>"
                               + m.group(1).replace("&", "&amp;")
                                            .replace("<", "&lt;")
                               + "</code></pre>",
                     md_text, flags=re.DOTALL)
    return md_text


def build() -> Path:
    parts = [COVER]

    # Front matter: the book README minus its own title line
    intro = (BOOK / "README.md").read_text(encoding="utf-8")
    parts.append("<div class='toc'>" + markdown.markdown(
        preprocess(intro), extensions=["tables", "fenced_code"]) + "</div>")

    for name in CHAPTER_FILES:
        md_text = (BOOK / "chapters" / name).read_text(encoding="utf-8")
        parts.append(markdown.markdown(
            preprocess(md_text), extensions=["tables", "fenced_code"]))

    html = ("<html><head><meta charset='utf-8'>"
            f"<style>{CSS}</style></head><body>"
            + "\n".join(parts) + "</body></html>")

    HTML(string=html).write_pdf(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"built {path}  ({path.stat().st_size / 1024:.0f} KB)")
