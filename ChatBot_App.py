import streamlit as st
from main import run_llm_query

st.title("Reglamento de Evaluación Chatbot")

# Inicializar el estado de la sesión para los mensajes
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Mostrar mensajes existentes
for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).write(msg["content"])


if user_input := st.chat_input():  # Verifica si hay entrada de usuario
    st.session_state["messages"].append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    try:
        # Ejecutar la consulta y mostrar la respuesta
        response = run_llm_query(user_input)
        st.session_state["messages"].append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)

    except Exception as e:
        st.error(f"Ocurrió un error al comunicarse con la API: {e}")
