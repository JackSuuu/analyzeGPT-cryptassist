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
from langchain.prompts import PromptTemplate  # Add this import

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
CSV_PATH = "./binance_data.csv"  # Change this to your actual CSV file path
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

# ... (keep all previous imports and setup code unchanged)

# --- Modified CSV Query Function ---
def create_csv_tool(llm, max_samples=3):
    """Create CSV tool with crypto analyst persona"""
    system_prompt = """You are a professional cryptocurrency market analyst. Analyze the CSV data with these rules:
1. Focus on price patterns, volatility, and market trends
2. Identify potential arbitrage opportunities
3. Highlight suspicious trading activity
4. Explain technical indicators where relevant
5. Maintain professional tone with clear insights"""

    data_context = f"""
**Dataset Overview**
- Total entries: {len(df)}
- Columns: {', '.join(df.columns)}
- Sample data:
{df.head(max_samples).to_string(index=False)}
"""

    def query_csv(query):
        """Enhanced crypto analysis using LLM"""
        full_prompt = f"{system_prompt}\n\n{data_context}\n\nQuery: {query}"
        try:
            response = llm.invoke(full_prompt)
            return response
        except Exception as e:
            return f"Analysis error: {str(e)}"

    return Tool(
        name="Crypto_Market_Analysis",
        func=query_csv,
        description="Specialized tool for cryptocurrency market analysis including price trends, volatility patterns, and trading insights"
    )

# --- Modified ChromaDB Query Function --- 
def create_chroma_tool():
    """Create ChromaDB tool with technical analysis focus"""
    def query_chroma(query):
        vectordb = get_vector_store()
        retriever = vectordb.as_retriever(search_kwargs={"k": 3})
        
        # Create proper PromptTemplate
        qa_prompt = PromptTemplate.from_template(
            """You are a blockchain technical analyst. Use these steps:
            1. Analyze document context thoroughly
            2. Identify key technical indicators
            3. Relate findings to current crypto market conditions
            4. Highlight potential risks and opportunities
            
            Context: {context}
            Question: {question}"""
        )
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=llms["groq"],
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": qa_prompt}  # Now passing a proper template
        )
        return qa_chain.invoke(query)["result"]
    
    return Tool(
        name="Blockchain_Technical_Analysis",
        func=query_chroma,
        description="Deep technical analysis of blockchain protocols and whitepapers"
    )

# --- Updated Chatbot Function ---
def make_output(query, use_groq=True, mode="data"):
    """Generate analyst-style output"""
    try:
        # Select LLM
        llm = llms["groq" if use_groq else "ollama"]
        print(f"Activating {mode} mode with {'Groq' if use_groq else 'Ollama'}")

        # Create tools based on mode
        if mode == "data":
            tools = [create_csv_tool(llm)]
        elif mode == "knowledge":
            tools = [create_chroma_tool()]
        else:
            raise ValueError("Invalid mode - use 'data' or 'knowledge'")

        # Initialize specialized agent
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            agent_kwargs={
                'prefix': '''You are a professional cryptocurrency analyst. 
                Always maintain analytical rigor and market awareness.'''
            }
        )
        
        return agent.run(f"From {mode} perspective: {query}")
    
    except Exception as e:
        print(f"Analysis pipeline error: {str(e)}")
        raise

# ... (keep modify_output and remaining code unchanged)

# Example usage
if __name__ == "__main__":
    crypto_question = "Identify any abnormal price patterns in the recent data and potential causes"
    
    # Data mode analysis
    print("\n=== MARKET DATA ANALYSIS ===")
    print(make_output(crypto_question, mode="data"))
    
    # Knowledge mode analysis
    print("\n=== TECHNICAL KNOWLEDGE ANALYSIS ===")
    print(make_output("Explain the security implications of recent smart contract trends", mode="knowledge"))