import sys
import os
import httpx
import logging
from typing import List
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from sqlalchemy import func
from sqlalchemy.orm import Session

# --- 1. SETUP LOGGING ---
log_file_path = r"D:\Project\PaymentBlockChain\mcp_debug.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

logging.info("🚀 Starting MCP Server...")

try:
    # --- SETUP PATH & IMPORTS ---
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.append(parent_dir)

    load_dotenv(os.path.join(parent_dir, ".env"))

    from langchain_core.messages import HumanMessage
    from graph.workflow import build_graph
    from app.db.session import SessionLocal
    from app.models.knowledge import JiraKnowledge

except Exception as e:
    logging.critical(f"❌ CRITICAL ERROR during startup: {str(e)}", exc_info=True)
    sys.exit(1)

# Initialize MCP Server
mcp = FastMCP("Jira-Knowledge-Gateway")

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


# === HELPER FUNCTIONS ===

def _run_agent_sync(ticket_key: str) -> str:
    """Helper to run the single-ticket agent."""
    try:
        app = build_graph()

        # ✅ เพิ่ม config={"recursion_limit": 50} (จากเดิม 25)
        final_state = app.invoke(
            {"messages": [HumanMessage(content=f"Sync data for {ticket_key}")]},
            config={"recursion_limit": 50}
        )
        return final_state['messages'][-1].content
    except Exception as e:
        logging.error(f"Agent failed for {ticket_key}: {e}")
        return f"Failed: {e}"

def _search_jira_keys(jql: str) -> List[str]:
    """
    Helper to search Jira using the NEW /rest/api/3/search/jql endpoint.
    Ref: https://developer.atlassian.com/changelog/#CHANGE-2046
    Note: Uses 'nextPageToken' for pagination instead of 'startAt'.
    """
    if not JIRA_URL or not JIRA_API_TOKEN:
        raise ValueError("Missing Jira Config")

    # ✅ ใช้ Endpoint ใหม่ที่ถูกต้อง
    url = f"{JIRA_URL}/rest/api/3/search/jql"

    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    found_keys = []
    next_token = None  # ตัวแปรสำหรับเก็บ Token หน้าถัดไป
    max_results = 50

    logging.info(f"🔎 Executing JQL (v3 Enhanced): {jql}")

    while True:
        # ✅ Payload แบบใหม่
        payload = {
            "jql": jql,
            "fields": ["key"],
            "maxResults": max_results
        }

        # ถ้ามี Token (หน้า 2 เป็นต้นไป) ให้ใส่เข้าไปใน payload
        if next_token:
            payload["nextPageToken"] = next_token

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, auth=auth, headers=headers, json=payload)

            if resp.status_code != 200:
                error_msg = f"Jira Search Error ({resp.status_code}): {resp.text}"
                logging.error(error_msg)
                raise Exception(error_msg)

            data = resp.json()
            issues = data.get("issues", [])

            if not issues:
                break

            for issue in issues:
                found_keys.append(issue["key"])

            # ✅ อัปเดต Token สำหรับรอบถัดไป
            next_token = data.get("nextPageToken")

            # ถ้าไม่มี Token ส่งกลับมา แสดงว่าหมดข้อมูลแล้ว
            if not next_token:
                break

    return found_keys


def _get_last_sync_time() -> str:
    """Find the latest sync timestamp from our DB."""
    session: Session = SessionLocal()
    try:
        last_time = session.query(func.max(JiraKnowledge.last_synced_at)).scalar()
        if last_time:
            # ใช้ Format ที่ Jira ชอบ: 'yyyy-MM-dd HH:mm'
            return last_time.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        logging.error(f"DB Query Error: {e}")
    finally:
        session.close()
    return None


# === MCP TOOLS ===

@mcp.tool()
async def preview_jira_ticket(issue_key: str) -> str:
    """
    PREVIEW or READ-ONLY details of a Jira ticket.
    Expected Output: Text summary only.
    """
    logging.info(f"Tool called: preview_jira_ticket for {issue_key}")

    if not JIRA_URL or not JIRA_API_TOKEN:
        return "Error: JIRA_URL or JIRA_API_TOKEN not set."

    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, auth=auth, headers=headers)
            if response.status_code == 404:
                return f"Jira Ticket {issue_key} not found."
            if response.status_code != 200:
                return f"Error fetching Jira: {response.status_code}"

            data = response.json()
            fields = data.get("fields", {})
            summary = fields.get("summary", "No Summary")
            description = fields.get("description", "No Description")
            status = fields.get("status", {}).get("name", "Unknown")

            # แปลง Description (ซึ่งอาจเป็น Dict ใน v3) ให้เป็น string ง่ายๆ
            desc_text = str(description)[:1000]

            return f"""
            --- JIRA TICKET: {issue_key} ---
            Summary: {summary}
            Status: {status}
            Description: {desc_text}...
            --------------------------------
            """
        except Exception as e:
            return f"Exception occurred: {str(e)}"


@mcp.tool()
def save_jira_to_db(ticket_key: str) -> str:
    """ACTIONS: Fetch and SAVE/INSERT Jira ticket into Database."""
    logging.info(f"Tool called: save_jira_to_db for {ticket_key}")
    return _run_agent_sync(ticket_key)


@mcp.tool()
def sync_single_ticket(ticket_key: str) -> str:
    """ACTIONS: Sync ONE specific Jira ticket to Database."""
    logging.info(f"Tool called: sync_single_ticket for {ticket_key}")
    return _run_agent_sync(ticket_key)


@mcp.tool()
def sync_project_batch(project_key: str, incremental: bool = True) -> str:
    """
    ACTIONS: Batch Sync multiple tickets from a project.
    Args:
        project_key: The project Key (e.g. "SCRUM")
        incremental: True = Sync only updated tickets. False = Force full sync.
    """
    logging.info(f"Tool called: sync_project_batch (Project: {project_key}, Inc: {incremental})")

    jql = ""
    if incremental:
        last_sync = _get_last_sync_time()
        if last_sync:
            logging.info(f"Detected last sync time: {last_sync}")
            # ใช้ updated >= เพื่อกันพลาด
            jql = f"project = {project_key} AND updated >= '{last_sync}'"
        else:
            logging.info("No previous sync found. Full sync.")
            jql = f"project = {project_key}"
    else:
        jql = f"project = {project_key}"

    # Search Jira
    try:
        keys_to_sync = _search_jira_keys(jql)
    except Exception as e:
        return f"❌ Failed to search Jira: {e}"

    if not keys_to_sync:
        return f"✅ No updates found for project {project_key}."

    # Loop Sync
    results = [f"🔄 Syncing {len(keys_to_sync)} tickets..."]

    for i, key in enumerate(keys_to_sync, 1):
        logging.info(f"[{i}/{len(keys_to_sync)}] Processing {key}...")
        status = _run_agent_sync(key)

        # Log ผลสั้นๆ
        short_status = "✅ Saved" if "Saved" in status or "Success" in status else "⚠️ Check Log"
        results.append(f"{i}. {key}: {short_status}")

    summary = "\n".join(results)
    return f"Batch Process Completed:\n{summary}"


if __name__ == "__main__":
    logging.info("Run command executing...")
    try:
        mcp.run()
    except Exception as e:
        logging.critical(f"Server crashed: {e}", exc_info=True)