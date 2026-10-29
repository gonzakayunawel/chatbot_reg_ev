"""
Construye los artefactos de recuperación a partir del reglamento en Markdown.

Uso:
    python preprocessing_text_and_embeddings.py

Lee `data/reglamento.md` (generado por `scripts/convert_docx_to_markdown.py`),
lo divide en fragmentos respetando los títulos y artículos, calcula los
embeddings y reconstruye:

    text_chunks.txt      un fragmento por línea (alineado con el índice)
    chunk_vectors.ann    índice Annoy con los vectores de esos fragmentos
"""

import re
from pathlib import Path

from annoy import AnnoyIndex
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

MARKDOWN_FILE = Path("data/reglamento.md")
CHUNKS_FILE = Path("text_chunks.txt")
INDEX_FILE = Path("chunk_vectors.ann")

EMBEDDINGS_MODEL = "paraphrase-multilingual-mpnet-base-v2"
CHUNK_SIZE = 600   # caracteres, equivalente aproximado a 100 tokens en español
CHUNK_OVERLAP = 60
N_TREES = 10

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# Guion de corte de línea del Word: "compren-\ndiendo" -> "comprendiendo".
HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(\w)")


def read_markdown(path: Path) -> str:
    """Carga el Markdown y repara los cortes de palabra del documento original."""
    text = path.read_text(encoding="utf-8")
    return HYPHEN_BREAK_RE.sub(r"\1\2", text)


def split_into_sections(markdown: str) -> list[tuple[str, str]]:
    """Agrupa el texto por encabezado: [(título, cuerpo), ...].

    Se descarta el H1 del documento (solo repite el nombre del reglamento).
    """
    sections: list[tuple[str, list[str]]] = []
    heading = ""

    for line in markdown.split("\n"):
        match = HEADING_RE.match(line)
        if match:
            level, title = len(match.group(1)), match.group(2).strip()
            heading = "" if level == 1 else title
            sections.append((heading, []))
            continue
        if not sections:
            sections.append((heading, []))
        sections[-1][1].append(line)

    return [(title, "\n".join(body).strip()) for title, body in sections if body]


def split_text_into_chunks(
    sections: list[tuple[str, str]], chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Divide cada sección y antepone su título para no perder el contexto."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "; ", ", ", " "],
    )
    chunks: list[str] = []

    for title, body in sections:
        if not body:
            continue
        for chunk in splitter.split_text(body):
            chunk = chunk.lstrip(" .;:,").strip()
            content = f"{title}. {chunk}" if title and chunk else (title or chunk)
            # Un fragmento por línea: el índice Annoy se resuelve por posición.
            chunks.append(" ".join(content.split()))

    return chunks


def main() -> None:
    if not MARKDOWN_FILE.exists():
        raise SystemExit(
            f"No se encontró {MARKDOWN_FILE}. Ejecuta primero "
            "`python scripts/convert_docx_to_markdown.py`."
        )

    sections = split_into_sections(read_markdown(MARKDOWN_FILE))
    text_chunks = split_text_into_chunks(sections)
    print(f"Secciones: {len(sections)} | Fragmentos: {len(text_chunks)}")

    CHUNKS_FILE.write_text("\n".join(text_chunks) + "\n", encoding="utf-8")

    embeddings_model = SentenceTransformer(EMBEDDINGS_MODEL)
    chunk_vectors = embeddings_model.encode(text_chunks, show_progress_bar=True)

    vector_dim = chunk_vectors.shape[1]
    annoy_index = AnnoyIndex(vector_dim, "angular")

    for index, vector in enumerate(chunk_vectors):
        annoy_index.add_item(index, vector)

    annoy_index.build(N_TREES)
    annoy_index.save(str(INDEX_FILE))

    print(f"Escrito: {CHUNKS_FILE} ({len(text_chunks)} fragmentos)")
    print(f"Escrito: {INDEX_FILE} ({vector_dim} dimensiones, {N_TREES} árboles)")


if __name__ == "__main__":
    main()
