import json
import logging
import re
import subprocess
import os
import shutil
from typing import Dict, Any, Optional, List

# ... (Imports เครื่องมือ local_agent อื่นๆ เหมือนเดิม) ...
from local_agent.llm_client import query_qwen
from local_agent.tools.file_ops import list_files, read_file, write_file
from local_agent.tools.code_analysis import generate_skeleton

# ... (Imports Git Ops เหมือนเดิม) ...
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

# ==============================================================================
# 📍 CONFIGURATION
# ==============================================================================
# 1. โฟลเดอร์งานหลักของคุณ (ต้นฉบับ)
MAIN_REPO_PATH = r"D:\Project\PaymentBlockChain"

# 2. โฟลเดอร์ที่ให้ Agent ไปวิ่งเล่น (Sandbox)
# ** ต้องเป็นคนละโฟลเดอร์กับข้างบน **
AGENT_WORKSPACE = r"D:\WorkSpace\PaymentBlockChain_Agent"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DevAgent")


# ----------------------------------------------------
# 🆕 New Tool: Init Workspace Logic (Sandbox Mode)
# ----------------------------------------------------
def init_workspace(branch_name: str, base_branch: str = "main") -> str:
    """
    Sandbox Setup:
    1. Check if AGENT_WORKSPACE exists.
    2. If not, CLONE from MAIN_REPO_PATH.
    3. If exists, Pull latest changes.
    4. Switch directory to AGENT_WORKSPACE (Isolation).
    5. Create/Checkout feature branch.
    """
    try:
        # 1. สร้างโฟลเดอร์ Workspace ถ้ายังไม่มี
        if not os.path.exists(AGENT_WORKSPACE):
            logger.info(f"📂 Creating Sandbox at: {AGENT_WORKSPACE}")
            os.makedirs(AGENT_WORKSPACE, exist_ok=True)

            # Clone จาก Repo หลักมา (Local Clone เร็วมาก)
            logger.info("⚡ Cloning from main repo...")
            subprocess.run(f'git clone "{MAIN_REPO_PATH}" .', shell=True, cwd=AGENT_WORKSPACE, check=True)

        # 2. 🚀 ย้ายตัว Agent ไปสิงสถิตที่ Sandbox (สำคัญมาก!)
        os.chdir(AGENT_WORKSPACE)
        logger.info(f"📍 Agent switched to: {os.getcwd()}")

        # 3. เคลียร์ Workspace ให้สะอาด & อัปเดต
        # Fetch ล่าสุดจาก Origin (ซึ่งคือ MAIN_REPO_PATH ของเรา)
        subprocess.run(f"git fetch origin", shell=True, check=True, capture_output=True)

        # Checkout ไปที่ Base Branch ก่อน
        subprocess.run(f"git checkout {base_branch}", shell=True, check=True, capture_output=True)
        subprocess.run(f"git pull origin {base_branch}", shell=True, capture_output=True)

        # 4. สร้าง Branch ใหม่สำหรับงานนี้
        subprocess.run(f"git checkout -B {branch_name}", shell=True, check=True, capture_output=True)

        return f"✅ Sandbox Initialized:\n- Location: {AGENT_WORKSPACE}\n- Synced with Main Repo\n- On Branch: '{branch_name}'\n- SAFE to code here (Isolated)."

    except subprocess.CalledProcessError as e:
        return f"❌ Git Error: {e}"
    except Exception as e:
        return f"❌ Error initializing sandbox: {e}"


# ----------------------------------------------------
# Tools Registration
# ----------------------------------------------------
TOOLS: Dict[str, Any] = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "generate_skeleton": generate_skeleton,
    "init_workspace": init_workspace,
}

if GIT_ENABLED:
    TOOLS.update({
        "git_commit": git_commit_changes,
        "git_push": git_push_to_remote,
        "git_status": git_status
    })

# ----------------------------------------------------
# System Prompt (เน้นย้ำเรื่อง Sandbox)
# ----------------------------------------------------
SYSTEM_PROMPT = """
You are an AI Developer Agent (Qwen). 
Your goal is to implement features safely using Git in an ISOLATED SANDBOX.

*** CRITICAL RULES - READ CAREFULLY ***
1. **FIRST STEP IS ALWAYS** `init_workspace(branch_name="...")`.
   - Do NOT do anything else before this.
   - Do NOT assume the workspace is ready.
2. **DO NOT USE `task_complete` IMMEDIATELY.**
   - You MUST perform actions: `list_files` -> `read_file` -> `write_file` -> `git_commit`.
   - If you don't know which file to edit, use `list_files` to look around.
3. **ACTUAL CODING REQUIRED.**
   - Do not just say you refactored. You must use `write_file` to actually change the code.

TOOLS AVAILABLE:
1. init_workspace(branch_name, base_branch="main") -> MUST USE FIRST.
2. list_files(directory=".")
3. read_file(file_path)
4. write_file(file_path, content)
5. git_commit(message)
6. git_push(branch_name)
7. task_complete(summary) -> ONLY after work is done.

RESPONSE FORMAT (JSON ONLY):

Example:
{
  "action": "init_workspace",
  "args": { "branch_name": "feature/sandbox-test" }
}

Remember: Output ONLY JSON blocks.
"""


# ... (ส่วน _extract_all_jsons, execute_tool_dynamic, run_dev_agent_task เหมือนเดิม ไม่ต้องแก้) ...
# (แต่ต้องมี _extract_all_jsons ตัวที่ใช้ JSONDecoder ล่าสุดนะ)

def _extract_all_jsons(text: str) -> List[Dict[str, Any]]:
    """ แกะ JSON แบบอัจฉริยะ (ใช้ Decoder ของ Python เอง) """
    results = []
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(text):
        try:
            search = re.search(r"\{", text[pos:])
            if not search: break
            start_index = pos + search.start()
            obj, end_index = decoder.raw_decode(text, idx=start_index)
            if isinstance(obj, dict) and "action" in obj:
                results.append(obj)
            pos = end_index
        except:
            pos += 1
    return results


def execute_tool_dynamic(tool_name: str, args: Dict[str, Any]) -> str:
    if tool_name not in TOOLS:
        return f"Error: Unknown tool '{tool_name}'"
    try:
        func = TOOLS[tool_name]
        if hasattr(func, 'invoke'):
            return str(func.invoke(args))
        else:
            return str(func(**args))
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

        log_resp = response[:100] + "..." if len(response) > 100 else response
        logger.info(f"🤖 AI Response: {log_resp}")

        tool_calls = _extract_all_jsons(response)

        if not tool_calls:
            history.append({"role": "assistant", "content": response})
            continue

        step_outputs = []
        task_finished = False
        final_summary = ""

        for tool_call in tool_calls:
            action = tool_call.get("action")
            args = tool_call.get("args", {})

            if action == "task_complete":
                final_summary = args.get("summary", "Task finished.")
                task_finished = True
                break

            logger.info(f"🔧 Executing Tool: {action}")
            result = execute_tool_dynamic(action, args)
            step_outputs.append(f"Tool Output ({action}):\n{result}")

            if action == "init_workspace" and "❌" in result:
                logger.error("🛑 Init failed! Stopping task.")
                return f"FAILED: {result}"

        if task_finished:
            logger.info(f"✅ Task Completed: {final_summary}")
            return f"SUCCESS: {final_summary}"

        combined_output = "\n---\n".join(step_outputs)
        history.append({"role": "assistant", "content": response})
        history.append({"role": "user", "content": combined_output})

    return "❌ FAILED: Max steps reached."