import sys
import os
import httpx
import logging # <--- เพิ่ม
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# --- 1. SETUP LOGGING (สำคัญมากสำหรับการ Debug MCP) ---
# ตั้งชื่อไฟล์ Log ไว้ที่ Root Project เพื่อให้หาง่าย
log_file_path = r"D:\Project\PaymentBlockChain\mcp_debug.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

logging.info("🚀 Starting MCP Server...")

try:

    # --- FIX 1: จัดการ Path ให้ Python มองเห็นโฟลเดอร์ 'graph' และ 'app' ---
    # หา path ของโฟลเดอร์ปัจจุบัน
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # ถอยหลังไป 1 ขั้นเพื่อหา Root Project (D:\Project\PaymentBlockChain)
    parent_dir = os.path.dirname(current_dir)
    # เพิ่ม Root Project เข้าไปในรายการที่ Python จะค้นหาไฟล์
    sys.path.append(parent_dir)

    # โหลด .env จาก Root Project
    load_dotenv(os.path.join(parent_dir, ".env"))

    # --- FIX 2: Import สิ่งที่ต้องใช้ (หลังจากแก้ Path แล้วถึงจะ import ได้) ---
    from langchain_core.messages import HumanMessage
    from graph.workflow import build_graph

except Exception as e:
    logging.critical(f"❌ CRITICAL ERROR during startup: {str(e)}", exc_info=True)
    sys.exit(1)

# Initialize MCP Server
mcp = FastMCP("Jira-Knowledge-Gateway")

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")



@mcp.tool()
async def preview_jira_ticket(issue_key: str) -> str:
    """
        PREVIEW or READ-ONLY details of a Jira ticket.
        Use this when the user just wants to see content or answer a question.
        Expected Output: Text summary only.
        SIDE EFFECT: NONE (Does NOT save to database).
    """

    logging.info(f"Tool called: preview_jira_ticket for {issue_key}")

    if not JIRA_URL or not JIRA_API_TOKEN:
        return "Error: JIRA_URL or JIRA_API_TOKEN not set in environment."

    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}

    # Jira REST API URL
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, auth=auth, headers=headers)

            if response.status_code == 404:
                return f"Jira Ticket {issue_key} not found."

            if response.status_code != 200:
                return f"Error fetching Jira: {response.status_code} - {response.text}"

            data = response.json()
            fields = data.get("fields", {})

            # Format output for AI to understand easily
            summary = fields.get("summary", "No Summary")
            description = fields.get("description", "No Description")
            status = fields.get("status", {}).get("name", "Unknown")

            return f"""
            --- JIRA TICKET: {issue_key} ---
            Summary: {summary}
            Status: {status}
            Description: 
            {str(description)[:5000]} 
            --------------------------------
            """
        except Exception as e:
            return f"Exception occurred: {str(e)}"


@mcp.tool()
def save_jira_to_db(ticket_key: str) -> str:
    """
        ACTIONS: Fetch, Analyze, and SAVE/INSERT the Jira ticket into the PostgreSQL Database.
        Use this tool EXCLUSIVELY when the user mentions "Save", "Sync", "Database", "Ingest", or "Store".
        This triggers the Librarian Agent to update the Knowledge Base.
    """
    logging.info(f"Tool called: save_jira_to_db for {ticket_key}")
    try:
        # เรียกใช้ Graph (Agent)
        app = build_graph()

        logging.info(f"🔄 MCP Request: Syncing {ticket_key}...")

        # สั่งให้ Agent ทำงาน
        final_state = app.invoke({
            "messages": [HumanMessage(content=f"Sync data for {ticket_key}")]
        })

        # ส่งคำตอบสุดท้ายของ AI กลับไปให้คนเรียก
        return final_state['messages'][-1].content

    except Exception as e:
        return f"❌ Error syncing ticket: {str(e)}"

if __name__ == "__main__":
    # Run as Standard IO (Stdio) for integration with Claude Desktop / IDEs
    logging.info("🚀 MCP Server starting...")
    mcp.run()