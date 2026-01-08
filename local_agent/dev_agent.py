import json
import logging
import re
from typing import Dict, Any, Optional, List

# Import เครื่องมือ
from local_agent.llm_client import query_qwen
from local_agent.tools.file_ops import list_files, read_file, write_file
from local_agent.tools.code_analysis import generate_skeleton

# Import Git Ops
try:
    from graph.tools.git_ops import (
        git_create_branch,
        git_commit_changes,
        git_push_to_remote,
        git_status
    )

    GIT_ENABLED = True
except ImportError:
    logging.warning("⚠️ Could not import git_ops. Git capabilities disabled.")
    GIT_ENABLED = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DevAgent")

# ----------------------------------------------------
# รวม Tools ทั้งหมดไว้ที่เดียว
# ----------------------------------------------------
# ✅ แก้ตรงนี้: ใส่ Type Hint : Dict[str, Any] เพื่อบอก IDE ว่า "อย่าเรื่องมาก รับได้หมด"
TOOLS: Dict[str, Any] = {
    # File Tools เดิม
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "generate_skeleton": generate_skeleton,
}

if GIT_ENABLED:
    TOOLS.update({
        "git_new_branch": git_create_branch,
        "git_commit": git_commit_changes,
        "git_push": git_push_to_remote,
        "git_status": git_status
    })

SYSTEM_PROMPT = """
You are an AI Developer Agent (Qwen). 
Your responsibilities include implementing features, fixing bugs, AND managing version control (Git).

You have access to the following tools:
1. File Operations: 
   - list_files(directory=".")
   - read_file(file_path)
   - write_file(file_path, content)
2. Git Operations: 
   - git_new_branch(branch_name)
   - git_commit(message)
   - git_push(branch_name)
   - git_status()

GUIDELINES:
- Always check `list_files` or `git_status` first to understand the context.
- When starting a new task, CREATE A NEW BRANCH first (unless instructed otherwise).
- After finishing the code, ALWAYS COMMIT your changes with a descriptive message.
- If the user asks to "Finish" or "Save", push the code to remote.
- Think step-by-step.

RESPONSE FORMAT EXAMPLES:

Example 1: List files
{
  "action": "list_files",
  "args": {
    "directory": "."
  }
}

Example 2: Create a new branch
{
  "action": "git_new_branch",
  "args": {
    "branch_name": "feature/login"
  }
}

Example 3: Write a file
{
  "action": "write_file",
  "args": {
    "file_path": "hello.py",
    "content": "print('Hello')"
  }
}

Example 4: Finish task
{
  "action": "task_complete",
  "args": {
    "summary": "Created branch and file successfully."
  }
}

Remember: ALWAYS respond with a JSON block like the examples above. """


def _extract_all_jsons(text: str) -> List[Dict[str, Any]]:
    """
    แกะ JSON ทั้งหมดที่หาเจอในข้อความ
    (รองรับกรณี AI ตอบหลายคำสั่งต่อกัน เช่น Create Branch -> Write File)
    """
    results = []
    try:
        # ---------------------------------------------------------
        # Pattern 1: หาแบบมีกรอบ ```json ... ``` (มาตรฐานที่สุด)
        # ---------------------------------------------------------
        # re.DOTALL ช่วยให้ .* อ่านข้ามบรรทัดได้
        matches = re.finditer(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match.group(1))
                results.append(data)
            except json.JSONDecodeError:
                pass

        # ---------------------------------------------------------
        # Pattern 2: ถ้าไม่เจอแบบมีกรอบ ให้หาแบบดิบๆ { ... }
        # ---------------------------------------------------------
        # ใช้เงื่อนไข if not results เพื่อป้องกันการซ้ำซ้อน (ถ้าเจอ Pattern 1 แล้วจะไม่ทำอันนี้)
        if not results:
            # ใช้ non-greedy match (.*?) เพื่อแยก JSON ทีละก้อน ไม่ให้รวบเป็นก้อนเดียว
            matches_raw = re.finditer(r"(\{.*?\})", text, re.DOTALL)
            for match in matches_raw:
                try:
                    obj = json.loads(match.group(1))

                    # ✅ ตัวกรองสำคัญ: ต้องมี key "action" เท่านั้นถึงจะนับเป็นคำสั่ง
                    # (ป้องกันไปหยิบ json มั่วๆ ในคำพูด AI มา)
                    if "action" in obj:
                        results.append(obj)
                except json.JSONDecodeError:
                    pass

    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")

    return results

def execute_tool_dynamic(tool_name: str, args: Dict[str, Any]) -> str:
    """
    ฟังก์ชันอัจฉริยะ: รัน Tool อัตโนมัติโดยเช็คประเภทของ Tool ให้เอง
    """
    # 1. เช็คว่ามี Tool ชื่อนี้ไหม
    if tool_name not in TOOLS:
        return f"Error: Unknown tool '{tool_name}'"

    try:
        func = TOOLS[tool_name]

        # 2. กรณีเป็น LangChain Tool (พวก Git Ops มักจะเป็นแบบนี้)
        # LangChain Tool ต้องเรียกใช้ผ่าน .invoke() และรับ dict ก้อนเดียว
        if hasattr(func, 'invoke'):
            return str(func.invoke(args))

        # 3. กรณีเป็น Python Function ปกติ (File Ops ของเรา)
        # ต้องกระจาย arguments ด้วย **args
        else:
            return str(func(**args))

    except TypeError as e:
        return f"Error arguments mismatch for '{tool_name}': {e}"
    except Exception as e:
        return f"Error executing {tool_name}: {e}"


def run_dev_agent_task(task_description: str, max_steps: int = 15) -> str:
    """
    Main Loop ที่รองรับ Multi-Action (ทำคำสั่ง Git รวดเดียวจบ)
    """
    logger.info(f"🚀 Starting Task: {task_description}")

    history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task_description}"}
    ]

    for step in range(max_steps):
        logger.info(f"🔄 Step {step + 1}/{max_steps}...")

        # 1. ถาม AI
        response = query_qwen(history)

        # Log คำตอบ (ตัดสั้นๆ)
        log_resp = response[:100] + "..." if len(response) > 100 else response
        logger.info(f"🤖 AI Response: {log_resp}")

        # 2. แกะ JSON ออกมาเป็น List (แก้จุดนี้เพื่อให้รับหลายคำสั่งได้)
        tool_calls = _extract_all_jsons(response)

        if not tool_calls:
            # ถ้าไม่มี Tool ให้คุยเล่นต่อ (แต่ปกติ System Prompt เราห้ามไว้)
            history.append({"role": "assistant", "content": response})
            continue

        # 3. วนลูปทำทุกคำสั่งที่ AI ส่งมา (Batch Execution)
        step_outputs = []
        task_finished = False
        final_summary = ""

        for tool_call in tool_calls:
            action = tool_call.get("action")
            args = tool_call.get("args", {})

            # ถ้าเจอคำสั่งจบงาน
            if action == "task_complete":
                final_summary = args.get("summary", "Task finished.")
                task_finished = True
                break  # หยุดลูป Tool ทันที

            logger.info(f"🔧 Executing Tool: {action}")

            # เรียกใช้ execute_tool_dynamic ที่เราเตรียมไว้
            result = execute_tool_dynamic(action, args)

            # เก็บผลลัพธ์
            step_outputs.append(f"Tool Output ({action}):\n{result}")

        # 4. ถ้ามีคำสั่ง task_complete ให้จบ Loop ใหญ่ทันที
        if task_finished:
            logger.info(f"✅ Task Completed: {final_summary}")
            return f"SUCCESS: {final_summary}"

        # 5. ส่งผลลัพธ์ทั้งหมดกลับไปให้ AI รู้ (รวมเป็นก้อนเดียว)
        combined_output = "\n---\n".join(step_outputs)

        history.append({"role": "assistant", "content": response})
        history.append({"role": "user", "content": combined_output})

    return "❌ FAILED: Max steps reached."