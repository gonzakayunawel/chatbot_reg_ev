"""
Núcleo de recuperación y generación.

Independiente de la interfaz: `app.py` (Chainlit) o cualquier otro cliente
pueden consumir `retrieve()` y `stream_answer()`.
"""

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import AsyncIterator

from annoy import AnnoyIndex
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

import config

MAX_LABEL_LEN = 90


@dataclass(frozen=True)
class Fragment:
    """Fragmento del reglamento recuperado para una consulta."""

    position: int
    text: str

    @property
    def label(self) -> str:
        """Rótulo legible: inicio del fragmento, útil para identificarlo."""
        text = " ".join(self.text.split())
        if len(text) <= MAX_LABEL_LEN:
            return text
        cut = text[:MAX_LABEL_LEN].rsplit(" ", 1)[0]
        return f"{cut}…"

    @property
    def excerpt(self) -> str:
        """Texto completo del fragmento, sin el prefijo del rótulo."""
        return self.text


@lru_cache(maxsize=1)
def _embeddings_model() -> SentenceTransformer:
    return SentenceTransformer(config.EMBEDDINGS_MODEL)


@lru_cache(maxsize=1)
def _index() -> AnnoyIndex:
    index = AnnoyIndex(config.VECTOR_DIM, "angular")
    index.load(str(config.INDEX_FILE))
    return index


@lru_cache(maxsize=1)
def _chunks() -> tuple[str, ...]:
    with open(config.CHUNKS_FILE, encoding="utf-8") as handle:
        return tuple(line.strip() for line in handle if line.strip())


@lru_cache(maxsize=1)
def _async_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=config.get_api_key(), base_url=config.LLM_BASE_URL)


def retrieve(question: str, k: int = config.TOP_K) -> list[Fragment]:
    """Devuelve los `k` fragmentos del reglamento más cercanos a la consulta."""
    vector = _embeddings_model().encode(question)
    positions = _index().get_nns_by_vector(vector, k)
    chunks = _chunks()
    return [Fragment(position=position, text=chunks[position]) for position in positions]


def build_prompt(question: str, fragments: list[Fragment]) -> str:
    """Compone el mensaje de usuario con el contexto recuperado."""
    context = "\n---\n".join(fragment.text for fragment in fragments)
    return f"Contexto del reglamento:\n```\n{context}\n```\n\nConsulta: {question}"


async def stream_answer(
    question: str,
    fragments: list[Fragment],
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    """Genera la respuesta en streaming, token a token."""
    messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": build_prompt(question, fragments)})

    request = {
        "model": config.LLM_MODEL,
        "temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
        "messages": messages,
        "stream": True,
    }
    if config.LLM_EFFORT:
        # Parámetro propio de DeepSeek; el SDK lo envía tal cual en el cuerpo.
        request["extra_body"] = {"effort": config.LLM_EFFORT}

    stream = await _async_client().chat.completions.create(**request)
    async for event in stream:
        if not event.choices:
            continue
        delta = event.choices[0].delta.content
        if delta:
            yield delta


def answer(question: str, history: list[dict] | None = None) -> tuple[str, list[Fragment]]:
    """Versión bloqueante, útil para pruebas y clientes no interactivos."""

    async def collect(fragments: list[Fragment]) -> str:
        return "".join([token async for token in stream_answer(question, fragments, history)])

    fragments = retrieve(question)
    return asyncio.run(collect(fragments)), fragments


def health() -> dict:
    """Comprueba que los artefactos de recuperación estén disponibles."""
    return {
        "fragmentos": len(_chunks()),
        "dimensión": _index().f,
        "modelo_embeddings": config.EMBEDDINGS_MODEL,
        "modelo_llm": config.LLM_MODEL,
        "razonamiento": config.LLM_EFFORT or "predeterminado",
        "endpoint_llm": config.LLM_BASE_URL,
        "top_k": config.TOP_K,
    }
