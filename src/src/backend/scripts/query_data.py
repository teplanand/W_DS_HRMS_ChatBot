import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import argparse
import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM
from langchain.prompts import ChatPromptTemplate
import re
from src.backend.scripts.get_embedding_function import get_embedding_function

CHROMA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', "chroma")


PROMPT_TEMPLATE="""
You are an HR assistant chatbot for GBS Technologies.
Provide a concise, professional response relevant to HR policies, procedures, or information outlined in the handbook. 
Answer the question based only on the given context below from the company handbook.
If there is even a little bit information related to question found than give that to the user.
Otherwise, don't try to make up an answer.
Act like you know these information and don't let user to know that you are using context from company handbook.

{context}

---

Question: {question}
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text
    query_rag(query_text)

def query_rag(query_text: str):
    persistent_client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_function = get_embedding_function()
    db = Chroma(
        client=persistent_client,
        embedding_function=embedding_function,
        collection_name="docs",
    )

    results = db.similarity_search_with_score(query_text, k=5)
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)

    model = OllamaLLM(model="llama3.2")
    raw_response = model.invoke(prompt)

    clean_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()
    sources = [doc.metadata.get("id", None) for doc, _score in results]
    formatted_response = f"Response:\n\n{clean_response}\n\nSources:\n\n{sources}"
    print(formatted_response)
    return clean_response

if __name__ == "__main__":
    main()