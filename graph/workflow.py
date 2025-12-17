from langgraph.graph import StateGraph, END
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

    app = build_graph()
    print("🚀 Running Simple Graph Test...")

    result = app.invoke({
        "messages": [HumanMessage(content="Hello LangGraph!")]
    })

    print(f"🏁 Final Result: {result['messages'][-1].content}")
