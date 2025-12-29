import os
import logging
from typing import List, Dict
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

# กำหนดที่เก็บ Vector DB (จะเป็น Folder ชื่อ 'chroma_db' ในโปรเจกต์)
PERSIST_DIRECTORY = os.path.join(os.getcwd(), "chroma_db")

# ตั้งค่า Embedding Model (ใช้ Ollama: nomic-embed-text)
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

# โหลด Vector DB เตรียมใช้งาน
vector_db = Chroma(
    collection_name="jira_knowledge",
    embedding_function=embeddings,
    persist_directory=PERSIST_DIRECTORY
)


def add_ticket_to_vector(ticket_data: Dict):
    """
    แปลงข้อมูล Ticket เป็น Vector แล้วยัดลง DB
    Ticket Data ต้องมี: key, summary, status, logic, spec
    """
    # 1. ปรุงข้อมูล: สร้าง Text ก้อนใหญ่ที่มีบริบทครบถ้วน
    # นี่คือส่วน 'Details' ที่คุณถามถึงครับ
    page_content = f"""
    TICKET: {ticket_data.get('key')}
    SUMMARY: {ticket_data.get('summary')}
    STATUS: {ticket_data.get('status')}

    [BUSINESS LOGIC]
    {ticket_data.get('logic') or 'N/A'}

    [TECHNICAL SPEC]
    {ticket_data.get('spec') or 'N/A'}
    """

    # 2. สร้าง Metadata (เอาไว้ filter ทีหลังได้)
    metadata = {
        "key": ticket_data.get('key'),
        "status": ticket_data.get('status'),
        "type": "jira_ticket"
    }

    # 3. บันทึกลง ChromaDB (ถ้ามีของเดิมทับไม่ได้ ต้องลบก่อน หรือปล่อยให้มันจัดการ ID เอง)
    # ในที่นี้เราใช้ key เป็น id ของ vector document เลย เพื่อกันซ้ำ
    logging.info(f"🧲 Vectorizing {ticket_data.get('key')}...")
    vector_db.add_documents(
        documents=[Document(page_content=page_content, metadata=metadata)],
        ids=[ticket_data.get('key')]
    )


def search_vector_db(query: str, k: int = 4):
    """ค้นหาข้อมูลด้วยความหมาย (Semantic Search)"""
    logging.info(f"🧠 Semantic Searching for: '{query}'")

    # ค้นหา k อันดับที่ใกล้เคียงที่สุด
    results = vector_db.similarity_search_with_score(query, k=k)

    parsed_results = []
    for doc, score in results:
        parsed_results.append(f"""
        --- MATCH (Score: {score:.2f}) ---
        {doc.page_content}
        -----------------------------------
        """)

    return "\n".join(parsed_results)