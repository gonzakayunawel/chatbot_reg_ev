"""
Configuración central del asistente.

Todos los parámetros ajustables del pipeline viven aquí para no repetirlos
entre la interfaz, el núcleo de recuperación y los scripts.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Artefactos generados por preprocessing_text_and_embeddings.py
CHUNKS_FILE = BASE_DIR / "text_chunks.txt"
INDEX_FILE = BASE_DIR / "chunk_vectors.ann"

# Recuperación
EMBEDDINGS_MODEL = "paraphrase-multilingual-mpnet-base-v2"
VECTOR_DIM = 768
TOP_K = 5

# Generación
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-flash")
# Nivel de razonamiento del modelo: low, high o max (vacío = valor del proveedor).
# Para consultas de extracción sobre un documento, "low" reduce latencia y costo.
LLM_EFFORT = os.getenv("LLM_EFFORT", "low")
API_KEY_ENV = "DEEPSEEK_API_KEY"
TEMPERATURE = 0.2
# Los tokens de razonamiento se descuentan de este límite.
MAX_TOKENS = 2000

SYSTEM_PROMPT = """Eres el asistente del Reglamento de Evaluación del Colegio \
Talagante Garden School. Respondes como parte de la Unidad Técnico Pedagógica, con \
dominio del reglamento y de la normativa educacional chilena que lo sustenta.

Reglas:
- Responde únicamente con la información del contexto entregado.
- Cita el artículo o título del reglamento del que proviene cada afirmación.
- Si el contexto no contiene la respuesta, dilo explícitamente e indica qué sección \
del reglamento conviene revisar; no inventes plazos, porcentajes ni procedimientos.
- Usa un registro formal y claro, sin mencionar tu rol ni el mecanismo de búsqueda.
"""


def get_api_key() -> str:
    """Devuelve la API key del proveedor LLM o falla con un mensaje accionable."""
    key = os.getenv(API_KEY_ENV)
    if not key:
        raise RuntimeError(
            f"Falta {API_KEY_ENV}. Defínela en el entorno o en el archivo .env "
            "de la raíz del proyecto."
        )
    return key
