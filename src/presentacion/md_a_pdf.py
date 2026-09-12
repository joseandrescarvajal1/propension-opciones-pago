# -*- coding: utf-8 -*-
"""Convierte los documentos de docs/ a PDF, con los diagramas de mermaid dibujados.

El markdown se pasa a HTML con estilo de documento y los bloques ```mermaid se renderizan en el
navegador (la librería se descarga del CDN, pero el contenido del diagrama nunca sale del equipo).
Después se imprime a PDF con Edge en modo sin ventana.

Uso:
    python src/presentacion/md_a_pdf.py                       # documento técnico y arquitectura
    python src/presentacion/md_a_pdf.py docs/otro.md          # uno concreto
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[2]
NAVEGADOR = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
POR_DEFECTO = ["docs/documento_tecnico.md", "docs/arquitectura.md"]

ESTILO = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", system-ui, sans-serif; font-size: 10.5pt; line-height: 1.55;
       color: #333; margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { font-size: 23pt; color: #2a78d6; margin: 0 0 4pt; font-weight: 700; letter-spacing: -0.3pt; }
h2 { font-size: 14pt; color: #2a78d6; margin: 20pt 0 6pt; font-weight: 700;
     border-bottom: 1.5pt solid #e3ebf5; padding-bottom: 3pt; break-after: avoid; }
h3 { font-size: 11.5pt; color: #1b3a5c; margin: 13pt 0 4pt; font-weight: 700; break-after: avoid; }
p { margin: 0 0 7pt; }
ul, ol { margin: 0 0 8pt; padding-left: 17pt; }
li { margin-bottom: 3pt; }
strong { color: #1b3a5c; }
code { background: #f1f4f8; padding: 1pt 3pt; border-radius: 2pt; font-size: 9pt;
       font-family: Consolas, monospace; color: #2a4a6b; }
pre { background: #f6f8fa; padding: 8pt; border-radius: 3pt; overflow-x: auto; font-size: 8.5pt; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 7pt 0 11pt; font-size: 9pt;
        break-inside: avoid; }
th { background: #edf2f8; text-align: left; font-weight: 700; color: #1b3a5c; }
th, td { border: 0.5pt solid #d5dde7; padding: 4pt 6pt; vertical-align: top; }
tr:nth-child(even) td { background: #fafbfd; }
hr { border: none; border-top: 0.5pt solid #dde4ec; margin: 16pt 0; }
blockquote { border-left: 2.5pt solid #2a78d6; margin: 8pt 0; padding: 2pt 0 2pt 10pt; color: #4a5568; }
.mermaid { text-align: center; margin: 14pt 0 18pt; break-inside: avoid; }
.mermaid svg { width: 100%; max-width: 100%; height: auto; }
a { color: #2a78d6; text-decoration: none; word-break: break-all; }
"""

PLANTILLA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>{titulo}</title>
<style>{estilo}</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
</head><body>
{cuerpo}
<script>
  mermaid.initialize({{ startOnLoad: true, theme: "base", securityLevel: "loose",
    themeVariables: {{ primaryColor: "#e8f0fa", primaryBorderColor: "#2a78d6", primaryTextColor: "#1b3a5c",
                       lineColor: "#6b7d91", fontFamily: "Segoe UI, sans-serif", fontSize: "17px" }},
    flowchart: {{ useMaxWidth: true, htmlLabels: true, padding: 12, nodeSpacing: 45, rankSpacing: 50 }} }});
</script>
</body></html>"""


def a_html(md_texto: str, titulo: str) -> str:
    cuerpo = markdown.markdown(md_texto, extensions=["tables", "fenced_code", "sane_lists", "attr_list"])
    # los bloques de mermaid deben quedar como <pre class="mermaid"> para que la librería los dibuje
    cuerpo = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>',
                    lambda m: '<pre class="mermaid">' + _desescapar(m.group(1)) + "</pre>",
                    cuerpo, flags=re.S)
    # una tabla clave-valor se escribe sin encabezados: si quedan vacios, se quita la fila
    cuerpo = re.sub(r"<thead>\s*<tr>(?:\s*<th[^>]*>\s*</th>)+\s*</tr>\s*</thead>", "", cuerpo, flags=re.S)
    return PLANTILLA.format(titulo=titulo, estilo=ESTILO, cuerpo=cuerpo)


def _desescapar(t: str) -> str:
    return t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')


def convertir(ruta_md: Path) -> Path:
    destino = ruta_md.with_suffix(".pdf")
    html = a_html(ruta_md.read_text(encoding="utf-8"), ruta_md.stem)
    tmp = ruta_md.with_suffix(".tmp.html")
    tmp.write_text(html, encoding="utf-8")
    n_diag = html.count('<pre class="mermaid">')
    try:
        subprocess.run([str(NAVEGADOR), "--headless", "--disable-gpu", "--no-sandbox",
                        f"--print-to-pdf={destino}", "--print-to-pdf-no-header",
                        "--no-pdf-header-footer",
                        "--virtual-time-budget=25000", tmp.resolve().as_uri()],
                       check=True, capture_output=True, timeout=180)
    finally:
        tmp.unlink(missing_ok=True)
    kb = destino.stat().st_size / 1024
    print(f"  {ruta_md.name:28s} -> {destino.name:28s} {kb:6.0f} KB   ({n_diag} diagramas)")
    return destino


def main():
    objetivos = sys.argv[1:] or POR_DEFECTO
    if not NAVEGADOR.exists():
        raise SystemExit(f"no encuentro el navegador en {NAVEGADOR}")
    print("convirtiendo a PDF:")
    for o in objetivos:
        p = Path(o) if Path(o).is_absolute() else ROOT / o
        if not p.exists():
            print(f"  {o}: no existe")
            continue
        convertir(p)
        time.sleep(1)


if __name__ == "__main__":
    main()
