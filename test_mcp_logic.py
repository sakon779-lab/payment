import sys
import os
import asyncio

# 1. Setup Path ให้ Python หาไฟล์เจอ
sys.path.append(os.getcwd())

# 2. Import ฟังก์ชันจาก MCP Server มาเทสตรงๆ
try:
    from mcp_server.main import save_jira_to_db, preview_jira_ticket
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Tip: ตรวจสอบว่ามีไฟล์ __init__.py ใน folder mcp_server หรือยัง?")
    sys.exit(1)


# 3. รันเทส
def run_tests():
    ticket_id = "SCRUM-13"  # หรือ SCRUM-2

    print("----------------------------------------------------------------")
    print(f"🧪 TESTING LOGIC FOR: {ticket_id}")
    print("----------------------------------------------------------------")

    # Test 1: Read (Fast)
    print("\n[1] Testing preview_jira_ticket (Async)...")
    try:
        # เพราะ preview_jira_ticket เป็น async ต้อง run ผ่าน loop
        result = asyncio.run(preview_jira_ticket(ticket_id))
        print("✅ Result:")
        print(result[:200] + "...")  # ตัดมาแค่ 200 ตัวอักษร
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Test 2: Sync (Agent + DB)
    print("\n[2] Testing save_jira_to_db (Agent)...")
    print("⏳ Waiting for Agent (Gemini) to process...")
    try:
        # save_jira_to_db เป็น sync function
        result = save_jira_to_db(ticket_id)
        print("✅ Result:")
        print(result)
    except Exception as e:
        print(f"❌ Failed: {e}")


if __name__ == "__main__":
    run_tests()