import os
import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize MCP Server
mcp = FastMCP("Jira-Knowledge-Gateway")

JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


@mcp.tool()
async def read_jira_ticket(issue_key: str) -> str:
    """
    Read details of a Jira ticket (Epic, Story, Task) by its Key (e.g., PAY-001).
    Returns the summary, description, and status.
    """
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

            # Note: Jira description is often ADF format, might need parsing in future.
            # For now, we return raw structure or plain text if available.

            return f"""
            --- JIRA TICKET: {issue_key} ---
            Summary: {summary}
            Status: {status}
            Description: 
            {description}
            --------------------------------
            """
        except Exception as e:
            return f"Exception occurred: {str(e)}"


if __name__ == "__main__":
    # Run as Standard IO (Stdio) for integration with Claude Desktop / IDEs
    mcp.run()