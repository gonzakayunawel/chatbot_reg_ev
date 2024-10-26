
import os, fitz, boto3, requests
from langchain.text_splitter import TokenTextSplitter
from sentence_transformers import SentenceTransformer
from annoy import AnnoyIndex
from io import BytesIO


PDF_INFO_FILE = os.getenv("PDF_INFO_FILE")

# Extraer el texto desde el archivo
def extract_text_from_pdf_from_url(pdf_url):
    """Extrae el texto desde un archivo PDF disponible en una URL."""
    response = requests.get(pdf_url)
    response.raise_for_status()  # Lanza un error si la descarga falla

    # Usar BytesIO para manejar el archivo como flujo de bytes
    pdf_stream = BytesIO(response.content)
    document = fitz.open(stream=pdf_stream, filetype="pdf")

    text = ""
    for page_num in range(document.page_count):
        page = document.load_page(page_num)
        text += page.get_text()

    return text

# Crear chunks del documento usando langchain


def split_text_into_chunks(file_content, chunk_size=100, chunk_overlap=10):
    text_splitter = TokenTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_text(file_content)
    return chunks


text = extract_text_from_pdf_from_url(PDF_INFO_FILE)
text_chunks = split_text_into_chunks(text)

print(type(text_chunks))

# with open("text_chunks.txt", "w") as f:
#     for chunk in text_chunks:
#         f.write(chunk + "\n")


# """## Calcular Embeddings"""



embeddings_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")

# # Convertir los fragmentos en vectores
chunk_vectors = embeddings_model.encode(text_chunks)

# """## Insertar los datos un base de datos vectorial"""



# Definir el número de dimensiones de los vectores
vector_dim = chunk_vectors.shape[1]

print(vector_dim)

# # Crear un índice Annoy
# annoy_index = AnnoyIndex(vector_dim, "angular")

# # Agregar vectores al índice
# for index, vector in enumerate(chunk_vectors):
#     annoy_index.add_item(index, vector)

# # Construir el índice (definir el número de árboles, mayor número da mejor precisión, pero más lento)
# n_trees = 10
# annoy_index.build(n_trees)

# # Guardar el índice en un archivo
# annoy_index.save("chunk_vectors.ann")

