import os
from typing import Literal
import langchain  # ✅ 1. เพิ่ม Import นี้

# --- Debug Mode: เปิดเพื่อให้เห็นว่า Llama ส่งอะไรกลับมา (สำคัญมาก) ---
langchain.debug = True

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from graph.state import AgentState
from graph.tools.database import save_ticket_knowledge
from graph.tools.jira import get_jira_ticket

from langchain_core.messages import AIMessage # เพิ่ม import นี้
import json

from langchain_core.messages import ToolMessage # อย่าลืม import เพิ่ม

# --- 1. Setup Brain (Ollama) & Tools ---

# Setup ให้ยิงเข้า Localhost ของเรา
llm = ChatOllama(
    model="llama3.1",
    temperature=0,
    base_url="http://localhost:11434",
    # ✅✅✅ เพิ่มบรรทัดนี้: ขยายความจำจาก 2k เป็น 8k หรือ 16k ✅✅✅
    num_ctx=16384
)

# รวม Tool ทั้งหมด
tools = [get_jira_ticket, save_ticket_knowledge]

# ผูก Tool เข้ากับสมอง
llm_with_tools = llm.bind_tools(tools)


# --- 2. Nodes ---

from langchain_core.messages import ToolMessage  # อย่าลืม import เพิ่ม


def agent_node(state: AgentState):
    messages = state['messages']

    tool_output_msg = next((m for m in reversed(messages) if isinstance(m, ToolMessage)), None)

    # 🛑 CHECKPOINT: ถ้า Save สำเร็จแล้ว จบงาน
    if tool_output_msg and "Successfully saved" in str(tool_output_msg.content):
        return {"messages": [AIMessage(content="✅ Sync Process Completed Successfully.")]}

    response = None

    if not tool_output_msg:
        # 🟢 PHASE 1: FETCHER
        print("--- PHASE 1: FETCHING ---")
        system_prompt = """ROLE: Jira Fetcher
        INSTRUCTIONS: Retrieve raw ticket data. Call 'get_jira_ticket' immediately."""

        phase_messages = [SystemMessage(content=system_prompt)] + messages[-1:]
        response = llm.bind_tools([get_jira_ticket], tool_choice="get_jira_ticket").invoke(phase_messages)

    else:
        # 🟠 PHASE 2: SAVER
        print("--- PHASE 2: SAVING (CLEAN SLATE) ---")
        raw_data_str = tool_output_msg.content

        system_prompt = """ROLE: Expert Jira Mapper

        TASK: Map INPUT TEXT to 'save_ticket_knowledge' tool.

        RULES:
        1. issue_key, summary, status, parent_key: Extract exactly.
        2. business_logic, technical_spec: Summarize from description.
        3. test_scenarios: Extract test cases.
        4. issue_links: Extract as List of JSON.

        ⛔ DO NOT CHAT. OUTPUT JSON TOOL CALL ONLY.
        """

        fresh_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"RAW DATA:\n{raw_data_str}")
        ]

        response = llm.bind_tools([save_ticket_knowledge], tool_choice="save_ticket_knowledge").invoke(fresh_messages)

    # 🔥🔥🔥 SAFETY NET: แก้ปัญหา AI พ่น JSON เป็น Text 🔥🔥🔥
    # ถ้า AI ไม่เรียก Tool (tool_calls ว่าง) แต่เนื้อหา (content) ดูเหมือน JSON
    if not response.tool_calls and response.content.strip().startswith('{'):
        try:
            print("⚠️ DETECTED FAKE TOOL CALL (TEXT JSON) - FIXING MANUALLY...")
            content_str = response.content.strip()

            # แปลง Text เป็น JSON
            data = json.loads(content_str)

            # ถ้าโครงสร้างตรงกับที่ Llama ชอบพ่นออกมา
            if "name" in data and "parameters" in data:
                # ยัดเยียดความเป็น Tool Call ให้มันซะ!
                response.tool_calls = [{
                    "name": data["name"],
                    "args": data["parameters"],
                    "id": "manual_fix_id"
                }]
                response.content = ""  # ลบ Text ออกเพื่อความเนียน
        except Exception as e:
            print(f"❌ Failed to parse fake tool call: {e}")

    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state['messages']
    last_message = messages[-1]

    # 1. ถ้า AI ไม่เรียก Tool แล้ว -> จบ
    if not last_message.tool_calls:
        return "__end__"

    # 2. ✅✅✅ Logic ดัดหลัง Llama 3.1 ✅✅✅
    # เช็คว่า "รอบที่แล้ว" เราเพิ่ง Save เสร็จไปหมาดๆ หรือไม่?
    # ถ้าใช่ แสดงว่า AI กำลังเอ๋อจะเรียกซ้ำ -> บังคับจบงานเลย
    if len(messages) > 2:
        prev_msg = messages[-2]  # ข้อความก่อนหน้า (น่าจะเป็น ToolMessage)
        if isinstance(prev_msg, ToolMessage):
            # ถ้าเพิ่ง Save เสร็จ ให้จบเลย ไม่ต้องไปต่อ
            # (ชื่อ Tool อาจต้องเช็คให้ตรงกับที่คุณตั้ง ในที่นี้สมมติ save_ticket_knowledge)
            if "save" in prev_msg.name.lower() or "database" in prev_msg.name.lower():
                return "__end__"

    # 3. ถ้าไม่มีอะไรผิดปกติ ก็ให้เรียก Tool ต่อไป
    return "tools"

# --- 3. Build Graph ---
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
    target_ticket = "SCRUM-16"

    print(f"📚 Librarian Agent (Ollama): Syncing {target_ticket}...\n")

    try:
        # ✅ เพิ่ม recursion_limit เพื่อป้องกันการตัดจบเร็วเกินไป
        final_state = app.invoke(
            {"messages": [HumanMessage(content=f"Sync data for {target_ticket}")]},
            config={"recursion_limit": 50}
        )

        print("\n--------------------------------")
        print("🕵️‍♀️ DEBUG: Tool Execution History")
        print("--------------------------------")

        for i, msg in enumerate(final_state['messages']):
            # ใช้ getattr เพื่อความปลอดภัย (ถ้าไม่มี attribute จะได้ค่าว่างแทน ไม่ Error)
            tool_calls = getattr(msg, 'tool_calls', [])
            content = getattr(msg, 'content', "")

            # 1. กรณีเป็น AI สั่งเรียก Tool
            if tool_calls:
                for tool in tool_calls:
                    print(f"[{i}] 🔧 AI Called Tool: {tool['name']}")

                    # ✅✅✅ เพิ่มบรรทัดนี้: เพื่อดูข้อมูลที่มันส่งไป Save ✅✅✅
                    import json

                    print(f"     📦 Payload: {json.dumps(tool['args'], indent=2, ensure_ascii=False)}")

            # 2. กรณีเป็นผลลัพธ์จาก Tool (ToolMessage)
            elif "ToolMessage" in str(type(msg)):
                # ตัดข้อความให้สั้นลงเพื่อให้อ่านง่าย
                output_preview = str(content)[:200].replace('\n', ' ')
                print(f"[{i}] 📤 Tool Output: {output_preview}...")

            # 3. กรณีเป็นข้อความสนทนา (Human หรือ AI บ่น)
            elif content:
                sender = "👤 User" if "HumanMessage" in str(type(msg)) else "🤖 AI"
                print(f"[{i}] {sender}: {content}")

        print("\n--------------------------------")

    except Exception as e:
        print(f"\n❌ Error: {e}")