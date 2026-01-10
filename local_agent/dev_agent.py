import json
import logging
import re
import subprocess
import os
import shutil
from typing import Dict, Any, Optional, List

# Import LLM Client
from local_agent.llm_client import query_qwen

# ❌ เราจะไม่ใช้ file_ops จากภายนอก เพื่อบังคับให้มันทำงานใน Sandbox Path เท่านั้น
# from local_agent.tools.file_ops import list_files, read_file, write_file
from local_agent.tools.code_analysis import generate_skeleton

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
# 1. โฟลเดอร์งานหลัก (Source)
MAIN_REPO_PATH = r"D:\Project\PaymentBlockChain"

# 2. โฟลเดอร์ Sandbox (Target)
AGENT_WORKSPACE = r"D:\WorkSpace\PaymentBlockChain_Agent"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DevAgent")


# ==============================================================================
# 🛠️ LOCAL FILE TOOLS (Override เพื่อบังคับใช้ Path ใน Sandbox)
# ==============================================================================
def list_files(directory: str = ".") -> str:
    """List files in the current sandbox directory."""
    try:
        files = []
        for root, _, filenames in os.walk(directory):
            if ".git" in root: continue
            for filename in filenames:
                files.append(os.path.relpath(os.path.join(root, filename), directory))
        if not files: return "No files found."
        return "\n".join(files[:50])
    except Exception as e:
        return f"Error listing files: {e}"


def read_file(file_path: str) -> str:
    """Read file content from current sandbox."""
    try:
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' not found in {os.getcwd()}"
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(file_path: str, content: str) -> str:
    """Write content to file in current sandbox."""
    try:
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ File written: {file_path} (in {os.getcwd()})"
    except Exception as e:
        return f"Error writing file: {e}"


# ==============================================================================
# 🛡️ SANDBOX & GIT TOOLS
# ==============================================================================
def init_workspace(branch_name: str, base_branch: str = "main") -> str:
    """
    Sandbox Setup: Clone -> Config Identity -> Checkout
    """
    try:
        # 1. Create/Clone Sandbox
        if not os.path.exists(AGENT_WORKSPACE):
            logger.info(f"📂 Creating Sandbox at: {AGENT_WORKSPACE}")
            os.makedirs(AGENT_WORKSPACE, exist_ok=True)
            logger.info("⚡ Cloning from main repo...")
            subprocess.run(f'git clone "{MAIN_REPO_PATH}" .', shell=True, cwd=AGENT_WORKSPACE, check=True)

        # 2. Switch Context
        os.chdir(AGENT_WORKSPACE)
        logger.info(f"📍 Agent switched to: {os.getcwd()}")

        # 3. Config Identity (Fix 'who are you' error)
        subprocess.run('git config user.name "AI Dev Agent"', shell=True, check=True)
        subprocess.run('git config user.email "ai_agent@local.dev"', shell=True, check=True)

        # 4. Sync & Checkout
        subprocess.run("git fetch origin", shell=True, check=True, capture_output=True)
        subprocess.run(f"git checkout {base_branch}", shell=True, check=True, capture_output=True)
        subprocess.run(f"git pull origin {base_branch}", shell=True, capture_output=True)
        subprocess.run(f"git checkout -B {branch_name}", shell=True, check=True, capture_output=True)

        return f"✅ Sandbox Initialized: Branch '{branch_name}' created from '{base_branch}'."

    except Exception as e:
        return f"❌ Error initializing sandbox: {e}"


def git_commit_wrapper(message: str) -> str:
    """Wrapper to handle 'nothing to commit' gracefully."""
    try:
        subprocess.run("git add .", shell=True, check=True)
        result = subprocess.run(f'git commit -m "{message}"', shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            return f"✅ Commit Success: {message}"
        else:
            msg = result.stderr + result.stdout
            if "nothing to commit" in msg:
                return "⚠️ Warning: Nothing to commit (Did you write any files?)"
            return f"❌ Commit Failed: {msg}"
    except Exception as e:
        return f"❌ Git Error: {e}"


# ----------------------------------------------------
# Tools Registration
# ----------------------------------------------------
TOOLS: Dict[str, Any] = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "generate_skeleton": generate_skeleton,
    "init_workspace": init_workspace,
    "git_commit": git_commit_wrapper,  # Use wrapper
}

if GIT_ENABLED:
    TOOLS.update({
        "git_push": git_push_to_remote,
        "git_status": git_status
    })

# ----------------------------------------------------
# System Prompt (Detailed Examples Preserved)
# ----------------------------------------------------
SYSTEM_PROMPT = """
You are an AI Developer Agent (Qwen). 
Your goal is to implement features safely using Git in an ISOLATED SANDBOX.

*** CRITICAL RULES ***
1. **FIRST STEP IS ALWAYS** `init_workspace(branch_name="...")`.
   - Do NOT do anything else before this.
2. **ACTUAL CODING REQUIRED.**
   - Use `write_file` to actually change the code.
   - Do not use `task_complete` until you have committed changes.

TOOLS AVAILABLE:
1. init_workspace(branch_name, base_branch="main") -> MUST USE FIRST.
2. list_files(directory=".")
3. read_file(file_path)
4. write_file(file_path, content)
5. git_commit(message)
6. git_push(branch_name)
7. task_complete(summary)

RESPONSE FORMAT (JSON ONLY):

Example 1: Initialize Workspace (Start Task)
{
  "action": "init_workspace",
  "args": {
    "branch_name": "feature/login-fix"
  }
}

Example 2: List files
{
  "action": "list_files",
  "args": {
    "directory": "."
  }
}

Example 3: Write a file
{
  "action": "write_file",
  "args": {
    "file_path": "utils/helper.py",
    "content": "def hello():\\n    print('Hello World')"
  }
}

Example 4: Commit Changes
{
  "action": "git_commit",
  "args": {
    "message": "Added helper function"
  }
}

Example 5: Finish task
{
  "action": "task_complete",
  "args": {
    "summary": "Initialized workspace, created helper.py, and committed changes."
  }
}

Remember: ALWAYS respond with a JSON block like the examples above.
"""


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

        # Log สั้นๆ
        logger.info(f"🤖 AI Response: {response[:100]}...")

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

            # Safety Check
            if action == "init_workspace" and "❌" in result:
                logger.error("🛑 Init failed! Stopping task.")
                return f"FAILED: {result}"

            # Log Success
            if "✅" in result:
                logger.info(f"✨ SUCCESS: {result}")

        if task_finished:
            logger.info(f"✅ Task Completed: {final_summary}")
            return f"SUCCESS: {final_summary}"

        combined_output = "\n---\n".join(step_outputs)
        history.append({"role": "assistant", "content": response})
        history.append({"role": "user", "content": combined_output})

    return "❌ FAILED: Max steps reached."