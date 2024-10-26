# Load libraries
from openai import OpenAI
from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer
from annoy import AnnoyIndex
import numpy as np

# Load Openai API KEY
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PDF_INFO_FILE = os.getenv("PDF_INFO_FILE")


# Respuesta del LLM usando un prompt
def query_llm(prompt, model="gpt-4o-mini"):
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Actúa como jefe de la unidad técnico pedagógica de un colegio o escuela, con nivel de experto en el rubro eductivo y en el reglamento de evaluación."},
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

    final_prompt = f"""Role: Actúa como jefe de la unidad técnico pedagógica de un colegio o escuela.
    Objective: Responde a la pregunta basándote en el reglamento de evaluación.
    Context: El contexto está delimitado por las comillas invertidas.

    ```
    {context}
    ```
    Pregunta: {question}
    """
    return query_llm(final_prompt)


def print_llm_response_in_short_lines(llm_response):
    """
    Prints the response of an LLM in lines that have a duration of 10 words as maximum.

    Args:
        llm_response: The response of the LLM.
    """

    # Split the response into words.
    words = llm_response.split()

    # Initialize the current line and the current word count.
    current_line = ""
    current_word_count = 0

    # Iterate over the words.
    for word in words:
        # If adding the current word would make the line too long, print the current line and start a new one.
        if current_word_count + len(word.split()) > 10:
            print(current_line)
            current_line = ""
            current_word_count = 0

        # Add the current word to the current line and update the word count.
        current_line += word + " "
        current_word_count += len(word.split())

    # Print the last line.
    print(current_line)
    

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

    print_llm_response_in_short_lines(get_answer(user_ask, potential_text))
