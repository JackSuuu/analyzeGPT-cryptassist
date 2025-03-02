import os
import time
import re
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from langchain_community.llms import Ollama
from langchain.chat_models import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.chains import RetrievalQA
import chromadb
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType

# Disable tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Configuration
PERSIST_DIR = Path("docs/chroma_db")
PERSIST_DIR.mkdir(exist_ok=True, parents=True)

# Load environment variables
load_dotenv()

# Embedding model
embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

# Initialize CSV data
CSV_PATH = "../binance_data.csv"  # Change this to your actual CSV file path
df = pd.read_csv(CSV_PATH)

# --- VECTOR STORE (ChromaDB) ---
def get_chroma_client():
    return chromadb.PersistentClient(path=str(PERSIST_DIR))

def get_vector_store():
    """Initialize vector store with error handling"""
    client = get_chroma_client()
    return Chroma(
        client=client,
        collection_name="main",
        embedding_function=embedding_function,
        persist_directory=str(PERSIST_DIR)
    )

# --- LLM Initialization ---
def initialize_llms():
    """Initialize LLMs with proper API key handling"""
    api_key = os.getenv("OPENAI_API_KEY")  # Use environment variable
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    return {
        "ollama": Ollama(model="deepseek-r1:1.5b"),
        "groq": ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.7,
            openai_api_key="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",
            openai_api_base="https://api.openai.com/v1"
        )
    }

# Initialize LLMs
llms = initialize_llms()

# --- CSV Query Function ---
def query_csv(query):
    """Handles structured CSV queries"""
    try:
        if "price" in query.lower():
            return f"Average price: {df['price'].mean():.2f}"
        elif "cheapest" in query.lower():
            return df.nsmallest(1, "price").to_string(index=False)
        elif "expensive" in query.lower():
            return df.nlargest(1, "price").to_string(index=False)
        else:
            return "I couldn't find an exact match in the CSV data."
    except Exception as e:
        return f"Error querying CSV: {str(e)}"

# --- ChromaDB Query Function ---
def query_chroma(query):
    """Handles semantic search in ChromaDB"""
    try:
        vectordb = get_vector_store()
        retriever = vectordb.as_retriever()
        qa_chain = RetrievalQA.from_chain_type(
            llm=llms["groq"],  # Default to Groq
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
        answer = qa_chain.invoke({"query": query})
        return answer["result"]
    except Exception as e:
        return f"Error in ChromaDB search: {str(e)}"

# --- Agent to Use CSV & ChromaDB Together ---
csv_tool = Tool(name="CSV Query", func=query_csv, description="For structured data queries.")
chroma_tool = Tool(name="ChromaDB Search", func=query_chroma, description="For semantic search on CSV data.")

# Create agent
agent = initialize_agent(
    tools=[csv_tool, chroma_tool],
    llm=llms["groq"],
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# --- Chatbot Function ---
def make_output(query, use_groq=True):
    """Generate chatbot output using CSV and ChromaDB"""
    try:
        print(f"Using {'Groq' if use_groq else 'Ollama'} chain")
        return agent.run(query)
    except Exception as e:
        print(f"Error in make_output: {str(e)}")
        raise

# --- Streaming Output ---
def modify_output(input_text):
    """Modified output with better streaming handling"""
    try:
        paragraphs = re.split(r'\n\s*\n', input_text)
        for para in paragraphs:
            if not para.strip():
                continue
            words = re.split(r'(\s+)', para)
            for word in words:
                if word.strip():
                    yield word + ' '
                    time.sleep(0.05)
            yield '\n\n'
    except Exception as e:
        print(f"Error in modify_output: {str(e)}")
        raise

# Example usage
if __name__ == "__main__":
    question = "What is the most expensive product?"
    response = make_output(question)
    print("Chatbot response:", response)
