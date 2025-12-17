import os
import httpx
from langchain_core.tools import tool


@tool
def get_jira_ticket(issue_key: str) -> str:
    """
    Fetches details of a Jira ticket (Summary, Status, Description) by its Key.
    Useful when you need to read requirements or checking status.
    Args:
        issue_key: The ID of the ticket, e.g., "PAY-001"
    """
    # ดึง Config จาก Environment
    jira_url = os.getenv("JIRA_URL")
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")

    # Check config
    if not all([jira_url, email, token]):
        return "Error: Jira credentials are missing in .env"

    auth = (email, token)
    headers = {"Accept": "application/json"}
    url = f"{jira_url}/rest/api/3/issue/{issue_key}"

    try:
        # ใช้ Synchronous Client (httpx) เพื่อความง่ายใน Graph
        with httpx.Client() as client:
            response = client.get(url, auth=auth, headers=headers)

            if response.status_code == 404:
                return f"Jira Ticket {issue_key} not found."
            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text}"

            data = response.json()
            fields = data.get("fields", {})

            # จัด format ข้อความให้ AI อ่านง่ายๆ
            description = fields.get('description', 'No Description')
            # (Optional) ถ้า Description เป็น dict แบบ ADF (Jira Cloud) อาจต้องแปลงเพิ่ม แต่เอาแบบดิบไปก่อน

            return f"""
            --- TICKET FOUND: {issue_key} ---
            Summary: {fields.get('summary')}
            Status: {fields.get('status', {}).get('name')}
            Description: {str(description)[:5000]} 
            ---------------------------------
            """
    except Exception as e:
        return f"Exception: {str(e)}"