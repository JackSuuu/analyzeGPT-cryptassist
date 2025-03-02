import os
import json
import logging
import shutil
import pandas as pd
import uuid
from pathlib import Path

from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

import chromadb

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Constants
PERSIST_DIR = Path("docs/chroma_db")
PERSIST_DIR.mkdir(exist_ok=True, parents=True)

def get_chroma_client():
    return chromadb.PersistentClient(path=str(PERSIST_DIR))

def process_chunks_and_generate_summary(chunks, source_name):
    """Process text chunks and add to existing collection"""
    embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    client = get_chroma_client()
    
    try:
        # Get or create collection
        collection = client.get_collection("main")
    except Exception as e:
        logger.info("Creating new main collection")
        collection = client.create_collection("main")

    # Generate unique IDs with source prefix
    ids = [f"{source_name}-{uuid.uuid4()}" for _ in chunks]
    
    # Add documents in batches
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        collection.add(
            documents=batch,
            ids=batch_ids,
            metadatas=[{"source": source_name} for _ in batch]
        )

    # Create langchain vector store
    vectordb = Chroma(
        client=client,
        collection_name="main",
        embedding_function=embedding_function
    )

    # Initialize LLM
    try:
        load_dotenv()
        llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.7,
            openai_api_key="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",
            openai_api_base="https://api.openai.com/v1"
        )
    except Exception as e:
        logger.error("Error initializing LLM: %s", e)
        raise e

    # Create QA chain
    try:
        retriever = vectordb.as_retriever()
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            verbose=False
        )
        
        # Generate summary based on csv or pdf file
        if source_name == "csv":
            prompt = "Analyze the crypto currency data and give very specific summary on it"
        elif source_name == "pdf":
            prompt = "Can you give me a summary of the context I gave, be super clear and explicit?"

        chain_result = qa_chain(prompt)
        answer = chain_result["result"]
        
        # Save summary
        with open("docs/summaries.json", "w") as f:
            json.dump({"summary": answer}, f)
            
        return answer

    except Exception as e:
        logger.error("Error in QA process: %s", e)
        raise e

def process_pdf(pdf_file_path: str) -> str:
    """Process PDF file and add to database"""
    logger.info("Processing PDF file: %s", pdf_file_path)
    try:
        reader = PdfReader(pdf_file_path)
        raw_text = "".join([page.extract_text() or "" for page in reader.pages])
        
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=1000,
            chunk_overlap=10,
            length_function=len
        )
        chunks = text_splitter.split_text(raw_text)
        return process_chunks_and_generate_summary(chunks, "pdf")

    except Exception as e:
        logger.error("PDF processing failed: %s", e)
        raise e
    finally:
        Path(pdf_file_path).unlink(missing_ok=True)

def process_csv(csv_file_path: str) -> str:
    """Process CSV file and add to database"""
    logger.info("Processing CSV file: %s", csv_file_path)
    try:
        df = pd.read_csv(csv_file_path)
        raw_text = "\n".join(
            [", ".join([f"{col}: {val}" for col, val in row.items()]) 
             for _, row in df.iterrows()]
        )
        
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=1000,
            chunk_overlap=10,
            length_function=len
        )
        chunks = text_splitter.split_text(raw_text)
        return process_chunks_and_generate_summary(chunks, "csv")

    except Exception as e:
        logger.error("CSV processing failed: %s", e)
        raise e
    finally:
        Path(csv_file_path).unlink(missing_ok=True)