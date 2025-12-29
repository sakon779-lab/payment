import os
from pathlib import Path

# Configuration of the Graph structure
graph_structure = {
    # 1. State Definition (ตัวแปรที่จะส่งต่อใน Graph)
    "graph/state.py": """from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph.message import add_messages
import operator

class AgentState(TypedDict):
    # message history (เก็บแชทที่คุยกัน)
    messages: Annotated[List[Any], add_messages]

    # context data (เก็บข้อมูลดิบที่ดึงมาจาก Jira/DB)
    jira_context: Dict[str, Any]

    # internal logic flags
    next_step: str
""",

    # 2. The Workflow (เส้นทางเดินของ Graph)
    "graph/workflow.py": """from langgraph.graph import StateGraph, END
from graph.state import AgentState

# --- Nodes (จุดทำงาน) ---
def agent_node(state: AgentState):
    print("--- 🤖 Agent is Processing ---")
    messages = state['messages']
    last_message = messages[-1]

    # Logic จำลอง: ถ้า user พิมพ์อะไรมา ก็ตอบกลับไป
    response = f"Agent Received: {last_message.content}"

    return {"messages": [("ai", response)]}

# --- Build Graph ---
def build_graph():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("agent", agent_node)

    # Set Entry Point (เริ่มที่ไหน)
    workflow.set_entry_point("agent")

    # Add Edges (ไปไหนต่อ)
    workflow.add_edge("agent", END)

    # Compile
    return workflow.compile()

# For Testing
if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    payment_core = build_graph()
    print("🚀 Running Simple Graph Test...")

    result = payment_core.invoke({
        "messages": [HumanMessage(content="Hello LangGraph!")]
    })

    print(f"🏁 Final Result: {result['messages'][-1].content}")
""",

    # 3. Empty Init files
    "graph/__init__.py": "",
    "graph/agents/__init__.py": "",
    "graph/tools/__init__.py": "",
}


def create_graph_structure():
    base_path = Path(".")

    print("🧠 Starting LangGraph Setup...")

    for file_path, content in graph_structure.items():
        full_path = base_path / file_path

        # Create directories
        if "/" in file_path:
            full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ Created: {file_path}")

    print("\n✨ LangGraph Structure Ready! ✨")
    print("Try running the test: python -m graph.workflow")


if __name__ == "__main__":
    create_graph_structure()