"""
Convierte el reglamento (.docx) a Markdown y normaliza su estructura.

Uso:
    python scripts/convert_docx_to_markdown.py

Busca el primer .docx en data/ (el nombre original viene en Unicode NFD, por lo
que se resuelve con glob en vez de escribir la ruta a mano), lo convierte con
MarkItDown y escribe data/reglamento.md.

El .docx no usa estilos de título de Word, así que MarkItDown devuelve párrafos
en negrita en lugar de encabezados. Este script los promueve a Markdown:

    **TÍTULO 1**                  ->  ## TÍTULO 1: PRESENTACIÓN
    **ARTÍCULO 7°:**              ->  ### ARTÍCULO 7°: <subtítulo>
    **N° 15 - Evaluación ...**    ->  #### N° 15 — Evaluación ...
"""

import re
from pathlib import Path

from markitdown import MarkItDown

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "reglamento.md"

# Imágenes embebidas: MarkItDown las deja como data URI truncado, sin texto útil.
IMAGE_RE = re.compile(r"!\[[^\]]*\]\((?:data:image/)?[^)]*\)")
# MarkItDown conserva el subrayado de Word como HTML; no aporta significado.
HTML_TAG_RE = re.compile(r"</?(?:u|em|strong|span|sub|sup|br)\s*/?>")

TITLE_RE = re.compile(r"^(T[IÍ]TULO)\s+([IVXLCDM]+|\d+)\s*[:.\-–]?\s*(.*)$", re.IGNORECASE)
ARTICLE_RE = re.compile(r"^(ART[IÍ]CULO)\s*(\d+)\s*[°º]?\s*[:.\-–]?\s*(.*)$", re.IGNORECASE)
NUMBERED_RE = re.compile(r"^N[°º]\s*(\d+)\s*[-–—]\s*(.+)$")
BOLD_LINE_RE = re.compile(r"^\*\*(.+?)\*\*[.:]?$")

HEADER = "# REGLAMENTO DE EVALUACIÓN, CALIFICACIÓN Y PROMOCIÓN 2024 — COLEGIO TGS"
MAX_SUBTITLE_LEN = 110


def strip_bold(line: str) -> str:
    """Quita el énfasis de una línea completa en negrita."""
    return line.replace("**", "").strip()


def clean_heading_text(text: str) -> str:
    """Normaliza el final de un título (sin puntos ni dos puntos colgando)."""
    return text.strip().rstrip(":").rstrip(".").strip()


def next_bold_subtitle(lines: list[str], start: int) -> tuple[int, str]:
    """Busca el primer título en negrita no vacío a partir de `start`.

    Devuelve (índice, texto) o (-1, "") si no hay. Se saltan las líneas en
    blanco porque Word separa el rótulo ("**TÍTULO 2**") de su nombre.
    """
    for j in range(start, min(start + 3, len(lines))):
        stripped = lines[j].strip()
        if not stripped:
            continue
        match = BOLD_LINE_RE.match(stripped)
        if not match:
            return -1, ""
        candidate = clean_heading_text(match.group(1))
        return (j, candidate) if looks_like_subtitle(candidate) else (-1, "")
    return -1, ""


def looks_like_subtitle(text: str) -> bool:
    """Heurística: línea corta, en mayúsculas y con contenido alfabético."""
    if not text or len(text) > MAX_SUBTITLE_LEN:
        return False
    if text[0].islower() or text[0].isdigit() or text[0] in "-–—•":
        return False
    return any(c.isalpha() for c in text)


def normalize(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    total = len(lines)

    while i < total:
        stripped = HTML_TAG_RE.sub("", lines[i]).strip()

        if not stripped:
            out.append("")
            i += 1
            continue

        # Se descartan las imágenes; las leyendas ("Cuadro N°4...") se conservan.
        if IMAGE_RE.fullmatch(stripped):
            i += 1
            continue

        is_bold_line = bool(BOLD_LINE_RE.match(stripped))
        plain = strip_bold(stripped)

        match = TITLE_RE.match(plain)
        if match:
            number, rest = match.group(2), match.group(3)
            heading = f"## TÍTULO {number}"
            if rest.strip():
                heading += f": {clean_heading_text(rest)}"
            else:
                # El nombre del título suele venir en la línea siguiente, en negrita.
                j, subtitle = next_bold_subtitle(lines, i + 1) if is_bold_line else (-1, "")
                if j != -1:
                    heading += f": {subtitle}"
                    i = j
            out.extend(["", heading, ""])
            i += 1
            continue

        match = ARTICLE_RE.match(plain)
        if match:
            number, rest = match.group(2), match.group(3)
            heading = f"### ARTÍCULO {number}°"
            if rest.strip():
                heading += f": {clean_heading_text(rest)}"
            elif is_bold_line:
                j, subtitle = next_bold_subtitle(lines, i + 1)
                if j != -1:
                    heading += f": {subtitle}"
                    i = j
            out.extend(["", heading, ""])
            i += 1
            continue

        match = NUMBERED_RE.match(plain)
        if match:
            out.extend(["", f"#### N° {match.group(1)} — {match.group(2).strip()}", ""])
            i += 1
            continue

        out.append(stripped)
        i += 1

    return out


def collapse_blank_lines(lines: list[str]) -> list[str]:
    collapsed: list[str] = []
    for line in lines:
        if not line and collapsed and not collapsed[-1]:
            continue
        collapsed.append(line)
    return collapsed


def main() -> None:
    candidates = sorted(DATA_DIR.glob("*.docx"))
    if not candidates:
        raise SystemExit(f"No se encontró ningún .docx en {DATA_DIR}")

    source = candidates[0]
    print(f"Convirtiendo: {source.name}")

    result = MarkItDown().convert(str(source))
    lines = collapse_blank_lines(
        normalize(result.text_content.replace("\r\n", "\n").split("\n"))
    )

    # El título original del documento se reemplaza por el encabezado H1.
    body: list[str] = []
    header_written = False
    for line in lines:
        if not header_written and not line.strip():
            continue
        if not header_written and "REGLAMENTO" in line.upper():
            header_written = True
            body.extend([HEADER, ""])
            continue
        body.append(line)

    OUTPUT_FILE.write_text("\n".join(body).strip() + "\n", encoding="utf-8")
    print(f"Escrito: {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
