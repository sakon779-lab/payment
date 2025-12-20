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


# def agent_node(state: AgentState):
#     messages = state['messages']
#
#     # 🕵️‍♀️ ตรวจสอบว่าในประวัติการคุย มีผลลัพธ์จาก Tool หรือยัง?
#     # (เช็คว่ามี message ที่เป็น ToolMessage หรือไม่)
#     has_tool_output = any(isinstance(m, ToolMessage) for m in messages)
#
#     if not has_tool_output:
#         # 🟢 PHASE 1: ยังไม่มีข้อมูล -> บังคับดึงข้อมูล (FETCHER MODE)
#         system_prompt = """ROLE: Jira Fetcher
#
#         Your ONLY Goal: Retrieve the raw ticket data.
#
#         INSTRUCTIONS:
#         1. You have received a ticket key (e.g., SCRUM-16).
#         2. You MUST call the tool 'get_jira_ticket' immediately.
#
#         ⛔ PROHIBITED:
#         - DO NOT call 'save_ticket_knowledge' yet. You don't have the data.
#         - DO NOT make up the summary.
#         """
#     else:
#         # 🟠 PHASE 2: SILENT EXECUTION MODE (ห้ามพูด ให้ทำเลย)
#         system_prompt = """ROLE: SYSTEM_PROCESS (NO HUMAN INTERACTION)
#
#         TASK:
#         You are a non-conversational middleware.
#         Your ONLY job is to Map Jira Data -> 'save_ticket_knowledge' Tool Call.
#
#         DATA MAPPING:
#         - Extract 'Business Logic', 'Technical Spec' from description (Convert List to String).
#         - Extract 'Issue Links' (List of JSON).
#         - Fill ALL fields.
#
#         ☠️ FATAL ERROR CONSTRAINTS (YOU MUST OBEY):
#         1. ❌ DO NOT speak or explain anything.
#         2. ❌ DO NOT output text like "Here is the tool call".
#         3. ❌ DO NOT output Markdown blocks (```python or ```json).
#         4. ❌ DO NOT simulate the code.
#
#         ✅ EXPECTED BEHAVIOR:
#         Trigger the tool function immediately and silently.
#         """
#
#     # ล้าง System Prompt เก่าออก (ถ้ามี) แล้วใส่ตัวใหม่ที่เราเลือกเข้าไปแทน
#     # (กรองเอาเฉพาะ message ที่ไม่ใช่ SystemMessage แล้วแปะอันใหม่ไว้หน้าสุด)
#     filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
#     messages = [SystemMessage(content=system_prompt)] + filtered_messages
#
#     # เช็คว่าเราอยู่ใน Phase ไหน?
#     if not has_tool_output:
#         # Phase 1: บังคับเรียก get_jira_ticket
#         response = llm.bind_tools([get_jira_ticket], tool_choice="get_jira_ticket").invoke(messages)
#     else:
#         # Phase 2: บังคับเรียก save_ticket_knowledge
#         response = llm.bind_tools([save_ticket_knowledge], tool_choice="save_ticket_knowledge").invoke(messages)
#
#     return {"messages": [response]}

def agent_node(state: AgentState):
    messages = state['messages']

    # เช็คว่ามีข้อมูลจาก Tool (get_jira_ticket) หรือยัง
    tool_output_msg = next((m for m in reversed(messages) if isinstance(m, ToolMessage)), None)

    if not tool_output_msg:
        # 🟢 PHASE 1: FETCHER (ยังไม่มีของ ไปเอาของมาก่อน)
        print("--- PHASE 1: FETCHING ---")
        system_prompt = """ROLE: Jira Fetcher
        INSTRUCTIONS: Retrieve the raw ticket data for the user.
        CMD: Call 'get_jira_ticket' immediately."""

        # สร้าง Message ชุดใหม่สำหรับ Phase นี้
        phase_messages = [SystemMessage(content=system_prompt)] + messages[-1:]  # เอาแค่ User message ล่าสุด

        response = llm.bind_tools([get_jira_ticket], tool_choice="get_jira_ticket").invoke(phase_messages)

    else:
        # 🟠 PHASE 2: CLEAN SLATE SAVER (ล้างสมอง แล้วยัดข้อมูลใส่ปาก)
        print("--- PHASE 2: SAVING (CLEAN SLATE) ---")

        # ดึงข้อมูลดิบออกมาจาก ToolMessage
        raw_data_str = tool_output_msg.content

        system_prompt = """ROLE: JSON Data Mapper (Strict Mode)

        Your ONLY Job: Map the INPUT TEXT into the 'save_ticket_knowledge' tool arguments.

        INPUT TEXT contains: Summary, Description, Status, etc.

        ⚠️ MAPPING RULES:
        1. issue_key, summary, status: Extract directly.
        2. business_logic: Summarize "What needs to be done" and "Rules" from the text. (Default: "General Logic")
        3. technical_spec: Extract "How to do it" (Libs, APIs, Servers). (Default: "General Spec")
        4. test_scenarios: Extract test cases. (Default: "N/A")

        ⛔ FATAL ERROR: DO NOT SPEAK. DO NOT SUMMARIZE. DO NOT EXPLAIN.
        ✅ ACTION: Call the tool 'save_ticket_knowledge' IMMEDIATELY.
        """

        # 🔥 สร้าง Context ใหม่เลย (ไม่เอาประวัติเก่ามาปน)
        # เราหลอก AI ว่า User เพิ่งส่งข้อมูลดิบมาให้ แล้วสั่งให้ Save เลย
        fresh_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"HERE IS THE RAW DATA TO MAP:\n\n{raw_data_str}")
        ]

        # บังคับเรียก Tool save_ticket_knowledge เท่านั้น
        response = llm.bind_tools([save_ticket_knowledge], tool_choice="save_ticket_knowledge").invoke(fresh_messages)

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