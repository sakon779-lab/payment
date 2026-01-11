import json
import logging
import re
import subprocess
import os
import shutil
from typing import Dict, Any, Optional, List

# Import LLM Client
from local_agent.llm_client import query_qwen

# ✅ Import เครื่องมือเดิม (ไม่ต้องเขียนใหม่)
from local_agent.tools.code_analysis import generate_skeleton as original_skeleton

# Import Git Ops
try:
    from graph.tools.git_ops import (
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
MAIN_REPO_PATH = r"D:\Project\PaymentBlockChain"
AGENT_WORKSPACE = r"D:\WorkSpace\PaymentBlockChain_Agent"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DevAgent")


# ==============================================================================
# 🛡️ SANDBOX WRAPPERS (ตัวกลางดักจับ Path)
# ==============================================================================

def safe_generate_skeleton(file_path: str) -> str:
    """
    Wrapper: บังคับให้ generate_skeleton อ่านไฟล์จาก Sandbox เท่านั้น
    """
    try:
        # 1. แปลงเป็น Full Path ใน Sandbox
        full_path = os.path.join(AGENT_WORKSPACE, file_path)

        # 2. เรียกใช้ฟังก์ชันเดิม (Modular)
        return original_skeleton(full_path)
    except Exception as e:
        return f"Error in skeleton wrapper: {e}"


# ... (list_files, read_file, write_file แบบ Local Override ยังคงไว้เหมือนเดิม เพื่อความชัวร์เรื่อง Path) ...

def list_files(directory: str = ".") -> str:
    """List files in the sandbox directory."""
    try:
        target_dir = os.path.join(AGENT_WORKSPACE, directory) if directory != "." else AGENT_WORKSPACE
        files = []
        for root, _, filenames in os.walk(target_dir):
            if ".git" in root: continue
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), AGENT_WORKSPACE)
                files.append(rel_path)
        if not files: return "No files found."
        files.sort()
        return f"📂 Project Structure ({len(files)} files):\n" + "\n".join(files[:100])
    except Exception as e:
        return f"Error: {e}"


def read_file(file_path: str) -> str:
    """Read file from sandbox."""
    try:
        full_path = os.path.join(AGENT_WORKSPACE, file_path)
        if not os.path.exists(full_path): return f"Error: File not found."
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"


def write_file(file_path: str, content: str) -> str:
    """Write file to sandbox."""
    try:
        full_path = os.path.join(AGENT_WORKSPACE, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ File written: {file_path}"
    except Exception as e:
        return f"Error: {e}"


# ✅ เพิ่มอันนี้: สำหรับต่อท้ายไฟล์ (ปลอดภัย ของเก่าไม่หาย)
def append_file(file_path: str, content: str) -> str:
    """
    APPEND content to the end of the file.
    Use this for adding new functions/classes without touching existing code.
    """
    try:
        full_path = os.path.join(AGENT_WORKSPACE, file_path)
        if not os.path.exists(full_path):
            return f"Error: File {file_path} does not exist. Use write_file to create it."

        with open(full_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + content)  # ขึ้นบรรทัดใหม่ให้สวยงาม
        return f"✅ Appended to: {file_path}"
    except Exception as e:
        return f"Error: {e}"


def init_workspace(branch_name: str, base_branch: str = "main") -> str:
    """Setup Sandbox: Clone -> Config -> Checkout"""
    try:
        if not os.path.exists(AGENT_WORKSPACE):
            logger.info(f"📂 Creating Sandbox at: {AGENT_WORKSPACE}")
            os.makedirs(AGENT_WORKSPACE, exist_ok=True)
            subprocess.run(f'git clone "{MAIN_REPO_PATH}" .', shell=True, cwd=AGENT_WORKSPACE, check=True)

        os.chdir(AGENT_WORKSPACE)
        subprocess.run('git config user.name "AI Dev Agent"', shell=True, cwd=AGENT_WORKSPACE, check=True)
        subprocess.run('git config user.email "ai_agent@local.dev"', shell=True, cwd=AGENT_WORKSPACE, check=True)

        subprocess.run(f"git fetch origin", shell=True, cwd=AGENT_WORKSPACE, check=True, capture_output=True)
        subprocess.run(f"git checkout {base_branch}", shell=True, cwd=AGENT_WORKSPACE, check=True, capture_output=True)
        subprocess.run(f"git pull origin {base_branch}", shell=True, cwd=AGENT_WORKSPACE, capture_output=True)
        subprocess.run(f"git checkout -B {branch_name}", shell=True, cwd=AGENT_WORKSPACE, check=True,
                       capture_output=True)

        return f"✅ Sandbox Ready: Branch '{branch_name}' active."
    except Exception as e:
        return f"❌ Init failed: {e}"


def git_commit_wrapper(message: str) -> str:
    """Commit wrapper."""
    try:
        status = subprocess.check_output("git status --porcelain", shell=True, cwd=AGENT_WORKSPACE, text=True)
        if not status: return "⚠️ Warning: Nothing to commit."
        subprocess.run("git add .", shell=True, cwd=AGENT_WORKSPACE, check=True)
        result = subprocess.run(f'git commit -m "{message}"', shell=True, cwd=AGENT_WORKSPACE, capture_output=True,
                                text=True)
        if result.returncode == 0:
            return f"✅ Commit Success: {message}"
        else:
            return f"❌ Commit Failed: {result.stderr}"
    except Exception as e:
        return f"❌ Git Error: {e}"


# ----------------------------------------------------
# Tools Registration
# ----------------------------------------------------
TOOLS: Dict[str, Any] = {
    "list_files": list_files,
    "generate_skeleton": safe_generate_skeleton,  # ✅ ใช้ Wrapper แทนตัวจริง
    "read_file": read_file,
    "write_file": write_file,
    "append_file": append_file, # ✅ Register Tool ใหม่
    "init_workspace": init_workspace,
    "git_commit": git_commit_wrapper,
}

if GIT_ENABLED:
    TOOLS.update({"git_push": git_push_to_remote, "git_status": git_status})

# ----------------------------------------------------
# System Prompt (Updated to enforce Analysis First)
# ----------------------------------------------------
SYSTEM_PROMPT = """
You are an AI Developer Agent (Qwen). 
Your goal is to implement features in an ISOLATED SANDBOX.

*** JUNIOR DEV WORKFLOW ***
1. **INITIALIZE**: `init_workspace(branch_name="...")`
2. **EXPLORE**: `list_files()` to understand structure.
3. **ANALYZE**: `generate_skeleton(file_path)` to see existing logic.
   - Do NOT guess code. Read the skeleton first!
4. **IMPLEMENT**: `write_file(file_path, content)`
5. **SAVE**: `git_commit(message)`

TOOLS AVAILABLE:
1. init_workspace(branch_name, base_branch="main")
2. list_files(directory=".")
3. generate_skeleton(file_path) -> USAGE: args: {"file_path": "src/main.py"}
4. read_file(file_path)
5. write_file(file_path, content) -> ⚠️ OVERWRITES EVERYTHING
6. append_file(file_path, content) -> ✅ ADDS TO END (SAFER)
7. git_commit(message)
8. task_complete(summary)

RESPONSE FORMAT (JSON ONLY):

Example 1: Analyze Structure
{
  "action": "generate_skeleton",
  "args": { "file_path": "local_agent/dev_agent.py" }
}

Example 2: Write Code
{
  "action": "write_file",
  "args": { "file_path": "utils.py", "content": "def help(): pass" }
}

Remember: ALWAYS respond with a JSON block.
"""


def _extract_all_jsons(text: str) -> List[Dict[str, Any]]:
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
    if tool_name not in TOOLS: return f"Error: Unknown tool '{tool_name}'"
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
        logger.info(f"🤖 AI Response: {response[:100]}...")

        tool_calls = _extract_all_jsons(response)
        if not tool_calls:
            history.append({"role": "assistant", "content": response})
            continue

        step_outputs = []
        task_finished = False

        for tool_call in tool_calls:
            action = tool_call.get("action")
            args = tool_call.get("args", {})
            if action == "task_complete":
                task_finished = True
                break

            logger.info(f"🔧 Executing Tool: {action}")
            result = execute_tool_dynamic(action, args)
            step_outputs.append(f"Tool Output ({action}):\n{result}")

            if action == "init_workspace" and "❌" in result:
                return f"FAILED: {result}"

        if task_finished:
            return "SUCCESS"

        combined_output = "\n".join(step_outputs)
        history.append({"role": "assistant", "content": response})
        history.append({"role": "user", "content": combined_output})

    return "❌ FAILED: Max steps reached."