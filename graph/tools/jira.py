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

            # --- 1. FIX PARENT KEY ---
            # ต้องเจาะไปเอา key ไม่ใช่เอาทั้ง object
            parent_info = fields.get("parent", {})
            parent_key = parent_info.get("key", "None")

            # --- 2. EXTRACT LINKS ---
            # ดึงความสัมพันธ์ออกมา (Blocks, Relates, etc.)
            raw_links = fields.get("issuelinks", [])
            formatted_links = []

            for link in raw_links:
                link_type = link.get("type", {}).get("name", "Related")

                # Link มี 2 ทาง: Outward (เราไป block เขา) / Inward (เขามา block เรา)
                if "outwardIssue" in link:
                    target = link["outwardIssue"]["key"]
                    direction = "outward"  # e.g. "blocks"
                    desc = link.get("type", {}).get("outward", link_type)
                elif "inwardIssue" in link:
                    target = link["inwardIssue"]["key"]
                    direction = "inward"  # e.g. "is blocked by"
                    desc = link.get("type", {}).get("inward", link_type)
                else:
                    continue

                formatted_links.append(f"- {desc} {target} ({direction})")

            links_text = "\n".join(formatted_links) if formatted_links else "None"

            # จัด format ข้อความให้ AI อ่านง่ายๆ
            description = fields.get('description', 'No Description')
            # (Optional) ถ้า Description เป็น dict แบบ ADF (Jira Cloud) อาจต้องแปลงเพิ่ม แต่เอาแบบดิบไปก่อน

            return f"""
            --- TICKET FOUND: {issue_key} ---
            Summary: {fields.get('summary')}
            Status: {fields.get('status', {}).get('name')}
            
            Parent Key: {parent_key}
            
            Linked Issues:
            {links_text}
            
            Description: {str(fields.get('description', 'No Description'))[:5000]}
            ---------------------------------
            """
    except Exception as e:
        return f"Exception: {str(e)}"