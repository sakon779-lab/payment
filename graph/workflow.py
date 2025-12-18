import os
from typing import Literal

# --- เปลี่ยน Import ตรงนี้ ---
from langchain_google_genai import ChatGoogleGenerativeAI  # <--- พระเอกของเรา
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from graph.state import AgentState
from graph.tools.database import save_ticket_knowledge
from graph.tools.jira import get_jira_ticket

# --- 1. Setup Brain (Gemini) & Tools ---

# ใช้ Gemini 1.5 Flash (เร็ว, ประหยัด) หรือ 1.5 Pro (ฉลาดกว่า แต่ช้ากว่านิดนึง)
llm = ChatGoogleGenerativeAI(
    model="gemini-flash-lite-latest",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# รวม Tool ทั้งหมด
tools = [get_jira_ticket, save_ticket_knowledge]

# ผูก Tool เข้ากับสมอง
llm_with_tools = llm.bind_tools(tools)


# --- 2. Nodes (เหมือนเดิม) ---

def agent_node(state: AgentState):
    messages = state['messages']

    # System Prompt: บรรณารักษ์
    system_prompt = """You are a strictly defined 'Knowledge Librarian' AI.
    Your GOAL: Read Jira tickets and save structured summaries to the database.

    PROCESS:
    1. Receive a Jira Ticket Key from the user (e.g., "Sync SCRUM-1").
    2. Use 'get_jira_ticket' to fetch raw content.
    3. ANALYZE the content and categorize it into:
       - Extract 'Parent Key' strictly from the provided text (if 'None', set to None).
       - Extract 'Linked Issues' into a list of objects: [{"relation": "blocks", "target_key": "PAY-XXX"}].
       - Business Logic: User flows, business rules, conditions.
       - Technical Spec: API endpoints, database fields, libraries, implementation details.
       - Test Scenarios: Acceptance criteria, test cases.
    4. Use 'save_ticket_knowledge' to save the result.

    RULES:
    - Do NOT make things up. If a section is missing, leave it as empty or "N/A".
    - For 'parent_key', ensure it is a Jira Key (e.g. SCRUM-1), NOT an ID.
    - If Link says "blocks SCRUM-2", relation is "blocks", target_key is "SCRUM-2".
    - Always identify 'issue_type' (Epic/Story/Task).
    - Once saved, confirm to the user with a short message like "✅ Saved [Key] to DB".
    """

    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=system_prompt)] + messages

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "tools"
    return "__end__"


# --- 3. Build Graph (เหมือนเดิม) ---
def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    return workflow.compile()


# --- For Testing ---
if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv()

    app = build_graph()

    # ใส่เลข Ticket จริงของคุณตรงนี้
    target_ticket = "SCRUM-2"

    print(f"📚 Librarian Agent (Gemini): Syncing {target_ticket}...")

    try:
        final_state = app.invoke({
            "messages": [HumanMessage(content=f"Sync data for {target_ticket}")]
        })
        print("\n🤖 Final Output:")
        print(final_state['messages'][-1].content)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Tip: เช็คว่าใส่ GOOGLE_API_KEY ใน .env หรือยัง?")