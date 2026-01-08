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
}

Remember: ALWAYS respond with a JSON block like the examples above. """


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        json_match_raw = re.search(r"(\{.*\})", text, re.DOTALL)
        if json_match_raw:
            return json.loads(json_match_raw.group(1))
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
    return None


def execute_tool_dynamic(tool_name: str, args: Dict[str, Any]) -> str:
    """
    ฟังก์ชันอัจฉริยะ: รัน Tool อัตโนมัติโดยไม่ต้องเขียน if-else เยอะๆ
    รองรับทั้ง Python Function ปกติ และ LangChain Tool (.invoke)
    """
    if tool_name not in TOOLS:
        return f"Error: Unknown tool '{tool_name}'"

    try:
        func = TOOLS[tool_name]

        # กรณี 1: เป็น LangChain Tool (พวก Git Ops มักจะเป็นแบบนี้)
        if hasattr(func, 'invoke'):
            # LangChain รับ input เป็น dict เดียว
            return str(func.invoke(args))

        # กรณี 2: เป็น Python Function ปกติ (File Ops ของเรา)
        else:
            # ใช้ **args เพื่อกระจาย dict เข้าไปเป็น parameter
            return str(func(**args))

    except TypeError as e:
        return f"Error arguments mismatch for '{tool_name}': {e}"
    except Exception as e:
        return f"Error executing {tool_name}: {e}"


def run_dev_agent_task(task_description: str, max_steps: int = 15) -> str:
    logger.info(f"🚀 Starting Task: {task_description}")

    history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task_description}"}
    ]

    for step in range(max_steps):
        logger.info(f"🔄 Step {step + 1}/{max_steps}...")

        response = query_qwen(history)

        # Log AI Response (ตัดให้สั้นลง)
        log_resp = response[:100] + "..." if len(response) > 100 else response
        logger.info(f"🤖 AI Response: {log_resp}")

        tool_call = _extract_json(response)

        if not tool_call:
            history.append({"role": "assistant", "content": response})
            continue

        # 3. เตรียมรัน Tool
        action = tool_call.get("action")
        args = tool_call.get("args", {})

        # Handle Task Complete
        if action == "task_complete":
            summary = args.get("summary", "Task finished.")
            logger.info(f"✅ Task Completed: {summary}")
            return f"SUCCESS: {summary}"

        logger.info(f"🔧 Executing Tool: {action}")

        # 4. เรียกใช้ฟังก์ชันผ่านตัวช่วย Dynamic
        result = execute_tool_dynamic(action, args)

        # 5. ส่งผลลัพธ์กลับ
        history.append({"role": "assistant", "content": response})
        history.append({"role": "user", "content": f"Tool Output ({action}):\n{result}"})

    return "❌ FAILED: Max steps reached."