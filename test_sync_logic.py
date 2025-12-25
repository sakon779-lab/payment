import sys
import os
import asyncio
from dotenv import load_dotenv

# --- 1. SETUP PATH ---
# บังคับให้ Python รู้จัก Folder ปัจจุบัน เพื่อให้ import mcp_server ได้
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# โหลด Environment Variables
load_dotenv()

print("🧪 STARTING LOGIC TEST...\n")

try:
    # --- 2. IMPORT ฟังก์ชันจาก mcp_server/main.py ---
    # เราจะดึงฟังก์ชันมาเทสตรงๆ เหมือนแกะเครื่องยนต์มาสตาร์ทข้างนอก
    from mcp_server.main import sync_project_batch, _search_jira_keys, _run_agent_sync

    # ==========================================
    # TEST CASE 1: ทดสอบการ Search (JQL)
    # ==========================================
    print("🔹 [TEST 1] Testing Jira Search Logic...")
    try:
        # ลองหาแค่ 2 ใบพอ (กันเหนียว)
        keys = _search_jira_keys(jql="project = SCRUM ORDER BY created DESC", max_fetch=2)
        print(f"   ✅ Search Result: Found {len(keys)} tickets -> {keys}")

        if not keys:
            print("   ⚠️ No tickets found. Skipping Sync Test.")
            sys.exit(0)

    except Exception as e:
        print(f"   ❌ Search Failed: {e}")
        sys.exit(1)

    print("-" * 30)

    # ==========================================
    # TEST CASE 2: ทดสอบการ Sync จริง (1 ใบ)
    # ==========================================
    target_ticket = keys[0]  # เอาใบแรกที่หาเจอมาเทส
    print(f"🔹 [TEST 2] Testing Agent Sync on '{target_ticket}'...")
    print("   ⏳ Agent is working (Checking Ollama & Graph)... please wait...")

    try:
        # เรียกฟังก์ชัน _run_agent_sync ตรงๆ
        result = _run_agent_sync(target_ticket)

        # เช็คผลลัพธ์
        if "Success" in result or "Saved" in result:
            print(f"   ✅ Sync Passed! Result:\n{result}")
        else:
            print(f"   ⚠️ Sync Finished but check output:\n{result}")

    except Exception as e:
        print(f"   ❌ Sync Failed: {e}")

    print("-" * 30)

    # ==========================================
    # TEST CASE 3: ทดสอบ Tool ใหญ่ (sync_project_batch)
    # ==========================================
    print(f"🔹 [TEST 3] Testing Full Batch Tool (Limit=1)...")
    # ลองเรียก Tool เหมือนที่ Claude จะเรียก (แต่จำกัด limit=1 เพื่อความไว)
    final_output = sync_project_batch(project_key="SCRUM", incremental=False, limit=1)

    print("\n📝 Final Output from Tool:")
    print(final_output)

except ImportError as e:
    print(f"\n❌ Import Error: หาไฟล์ไม่เจอ หรือ Path ผิด ({e})")
    print("ตรวจสอบว่าไฟล์ test_sync_logic.py อยู่ที่ Root Folder เดียวกับ .env ไหม")
except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")

print("\n🧪 TEST COMPLETED.")