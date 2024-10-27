# Load libraries
from openai import OpenAI
from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer
from annoy import AnnoyIndex
import numpy as np

import streamlit as st

# Load Openai API KEY
load_dotenv()
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
PDF_INFO_FILE = os.getenv("PDF_INFO_FILE")


# Respuesta del LLM usando un prompt
def query_llm(prompt, model="gpt-4o-mini"):
    
    system_prompt = """Actúa como jefe de la unidad técnico pedagógica de un colegio o escuela, con nivel de experto en el rubro eductivo y en el reglamento de evaluación.
    Responde a la pregunta basándote en el reglamento de evaluación. No digas tu rol, solo responde como un asistente para quien consulta. Tienes acceso a los siguientes documentos:
    - Reglamento de Evaluación del Colegio Talagante Garden School.
    """
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


# Ejemplo de pregunta


def user_prompt_example():
    user_ask = "¿Qué significa ser aspiracionista?"

    president_name = "Michelle Bachelet Jeria"

    prompt = f"""Eres {president_name}, presidente de Chile.
    Responde a la pregunta como si tu fueras {president_name}, teniendo en cuenta sus participaciones públicas.

    Pregunta: {user_ask}
    """

    llm_response = query_llm(prompt)
    print(llm_response)

# """## Generar la respuesta usando el LLM"""

embeddings_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")

def get_embedding(text: str) -> np.ndarray:
    """
    Obtiene la representación vectorial de un texto.
    Args:
        text: El texto a convertir en vectores.
    """
    return embeddings_model.encode(text)


# """### Hacer la pregunta"""


def get_answer(question: str, context_documents):
    """
    Hace la pregunta y devuelve la respuesta del LLM.
    Args:
        question: La pregunta a ser respondida.
        context_documents: Los documentos que componen el contexto.
    """
    context_divider = "\n---\n"
    question = question.strip()
    context = context_divider.join(context_documents)

    final_prompt = f"""
    ```
    {context}
    ```
    Pregunta: {question}
    """
    return query_llm(final_prompt)


def run_llm_query(user_ask):
    
    # This is a sentence-transformers model: 
    # It maps sentences & paragraphs to a 768 dimensional 
    # dense vector space and can be used for tasks like clustering or semantic search.
    
    
    annoy_index = AnnoyIndex(768, 'angular') # Vector dimension from SentenceTransformer
    annoy_index.load('chunk_vectors.ann')

    embedding_ask = get_embedding(user_ask)
    
    with open("text_chunks.txt", "r") as f:
        text_chunks = f.readlines()

    ids_potential_answers = annoy_index.get_nns_by_vector(embedding_ask, 5)
    potential_text = [text_chunks[idx] for idx in ids_potential_answers]

    return get_answer(user_ask, potential_text)
