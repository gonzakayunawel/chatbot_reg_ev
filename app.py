"""
Interfaz de chat del asistente (Chainlit).

Ejecutar con:
    chainlit run app.py -w

La lógica de recuperación y generación vive en `rag.py`; este módulo solo
orquesta la conversación.
"""

import logging

import chainlit as cl

import config
import rag

logger = logging.getLogger(__name__)

ASSISTANT_NAME = "Reglamento TGS"
MAX_HISTORY_MESSAGES = 6

WELCOME = (
    "Soy el asistente del **Reglamento Interno de Evaluación y Promoción Escolar "
    "2024** del Colegio Talagante Garden School.\n\n"
    "Respondo consultas sobre evaluación, calificación, promoción y "
    "acompañamiento pedagógico usando exclusivamente el texto del reglamento, "
    "e indico el artículo en que se basa cada respuesta."
)

ERROR_MESSAGE = (
    "No fue posible generar la respuesta en este momento. "
    "Vuelve a intentarlo en unos segundos; si el problema persiste, "
    "avisa al administrador del servicio."
)


@cl.on_chat_start
async def on_chat_start() -> None:
    cl.user_session.set("history", [])
    await cl.Message(content=WELCOME, author=ASSISTANT_NAME).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    question = message.content.strip()
    if not question:
        return

    async with cl.Step(name="Recuperando artículos del reglamento", type="retrieval") as step:
        fragments = await cl.make_async(rag.retrieve)(question)
        step.output = "\n".join(f"— {fragment.label}" for fragment in fragments)

    reply = cl.Message(content="", author=ASSISTANT_NAME)

    try:
        async with cl.Step(name="Redactando la respuesta", type="llm") as step:
            history = cl.user_session.get("history") or []
            async for token in rag.stream_answer(question, fragments, history):
                await reply.stream_token(token)
            step.output = f"{config.LLM_MODEL} · {len(fragments)} fragmentos de contexto"
    except Exception:
        logger.exception("Error al generar la respuesta")
        reply.content = ERROR_MESSAGE
        await reply.send()
        return

    reply.elements = [
        cl.Text(name=fragment.label, content=fragment.excerpt, display="side")
        for fragment in fragments
    ]
    await reply.send()

    history = cl.user_session.get("history") or []
    history.extend(
        [
            {"role": "user", "content": question},
            {"role": "assistant", "content": reply.content},
        ]
    )
    cl.user_session.set("history", history[-MAX_HISTORY_MESSAGES:])
