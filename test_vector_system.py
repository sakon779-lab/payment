# ไฟล์: test_vector_system.py
import sys
import os
import shutil

# 1. Setup Path
sys.path.append(os.getcwd())

from knowledge_base.vector_store import add_ticket_to_vector, search_vector_db, vector_db, PERSIST_DIRECTORY


def test_system():
    print(f"📂 Database Path: {PERSIST_DIRECTORY}")

    # 2. ลองสร้างข้อมูลจำลอง (ไม่ต้องผ่าน Server)
    test_key = "TEST-999"
    print(f"\n🧪 Step 1: Manually Adding {test_key}...")
    try:
        add_ticket_to_vector(
            issue_key=test_key,
            summary="Test Vector System",
            content="This is a dummy content to verify ChromaDB persistence."
        )
        print("✅ Function executed without error.")
    except Exception as e:
        print(f"❌ Error during add: {e}")
        return

    # 3. ลองอ่านทันที
    print(f"\n👀 Step 2: Reading back immediately...")
    data = vector_db.get(where={"issue_key": test_key})

    if data['ids']:
        print(f"✅ FOUND ID: {data['ids']}")
        print(f"✅ Metadata: {data['metadatas']}")
    else:
        print("❌ NOT FOUND! (Write failed silently)")

    # 4. ลอง Search
    print(f"\n🔎 Step 3: Semantic Search...")
    results = search_vector_db("dummy content", k=1)
    if results:
        print(f"✅ Search Result: {results}")
    else:
        print("❌ Search returned empty.")

    # 5. เช็คไฟล์จริง
    print(f"\n📂 Step 4: Checking Physical File...")
    sqlite_path = os.path.join(PERSIST_DIRECTORY, "chroma.sqlite3")
    if os.path.exists(sqlite_path):
        size = os.path.getsize(sqlite_path)
        print(f"✅ File exists: {sqlite_path}")
        print(f"📊 File size: {size / 1024:.2f} KB")
    else:
        print(f"❌ File missing: {sqlite_path}")


if __name__ == "__main__":
    test_system()