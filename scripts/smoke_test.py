"""
Verificación rápida del servicio.

Uso:
    python scripts/smoke_test.py          # artefactos y recuperación (sin costo)
    python scripts/smoke_test.py --llm    # además genera una respuesta real

Códigos de salida: 0 si todo pasa, 1 si falla alguna comprobación.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
import rag  # noqa: E402

# (consulta, fragmento que debe aparecer entre los recuperados)
CASES = [
    ("¿Cuál es el nivel de exigencia para obtener un 4.0?", "ARTÍCULO 24"),
    ("¿Qué porcentaje de asistencia se exige para ser promovido?", "ARTÍCULO 38"),
    ("¿Cuánto pondera el examen especial de fin de año?", "ARTÍCULO 28"),
    ("¿Qué pasa si un estudiante es sorprendido copiando?", "ARTÍCULO 21"),
]


def check(condition: bool, message: str) -> bool:
    print(f"{'OK  ' if condition else 'FALLA'} {message}")
    return condition


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true", help="probar también la generación")
    args = parser.parse_args()

    results: list[bool] = []

    # 1. Artefactos
    results.append(check(config.CHUNKS_FILE.exists(), f"existe {config.CHUNKS_FILE.name}"))
    results.append(check(config.INDEX_FILE.exists(), f"existe {config.INDEX_FILE.name}"))
    if not all(results):
        print("\nEjecuta preprocessing_text_and_embeddings.py para generarlos.")
        return 1

    chunks = rag._chunks()
    index = rag._index()
    results.append(check(len(chunks) > 0, f"fragmentos cargados: {len(chunks)}"))
    results.append(
        check(
            index.get_n_items() == len(chunks),
            f"índice alineado: {index.get_n_items()} vectores para {len(chunks)} fragmentos",
        )
    )
    results.append(check(index.f == config.VECTOR_DIM, f"dimensionalidad: {index.f}"))
    print(f"     modelo: {config.LLM_MODEL} · endpoint: {config.LLM_BASE_URL}")

    # 2. Recuperación
    for question, expected in CASES:
        labels = [fragment.label for fragment in rag.retrieve(question)]
        found = any(expected in label for label in labels)
        results.append(check(found, f"{expected} recuperado para «{question[:45]}…»"))

    # 3. Generación (opcional, consume cuota de la API)
    if args.llm:
        question = CASES[0][0]
        answer, fragments = rag.answer(question)
        results.append(check(len(answer.strip()) > 0, "respuesta no vacía"))
        results.append(check("artículo" in answer.lower(), "la respuesta cita un artículo"))
        results.append(check(len(fragments) == config.TOP_K, "se adjuntaron las fuentes"))
        print("\n--- respuesta ---")
        print(answer.strip())

    failed = results.count(False)
    print(f"\n{len(results) - failed}/{len(results)} comprobaciones correctas")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
