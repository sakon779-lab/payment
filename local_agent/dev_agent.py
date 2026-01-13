import json
import logging
import re
import subprocess
import os
import sys
import shutil
import ast
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Import LLM Client
from local_agent.llm_client import query_qwen

# ✅ IMPORT 1: Code Analysis Tool (Wrapper จะเรียกใช้ตัวนี้)
from local_agent.tools.code_analysis import generate_skeleton as original_skeleton

# ==============================================================================
# 📍 CONFIGURATION
# ==============================================================================
MAIN_REPO_PATH = r"D:\Project\PaymentBlockChain"
AGENT_WORKSPACE = r"D:\WorkSpace\PaymentBlockChain_Agent"

# ==============================================================================
# 🔑 SECURITY & ENVIRONMENT SETUP (แก้ปัญหา Sandbox หา Config ไม่เจอ)
# ==============================================================================
# ✅ 2. สั่งโหลด .env จาก MAIN_REPO_PATH โดยตรง
# ไม่ว่า Agent จะย้ายไปโฟลเดอร์ไหน ค่านี้จะยังอยู่ใน Memory
env_path = os.path.join(MAIN_REPO_PATH, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    logging.info(f"✅ Loaded environment variables from: {env_path}")
else:
    logging.warning(f"⚠️ .env file not found at: {env_path}")

# ตรวจสอบว่ามีค่า JIRA หรือไม่ (ถ้าไม่มี ให้ Set default หรือแจ้งเตือน)
if not os.getenv("JIRA_URL"):
    # กรณี User ไม่ได้ใส่ใน .env เราสามารถ Override ชั่วคราวตรงนี้ได้ (แต่ไม่แนะนำ)
    # os.environ["JIRA_URL"] = "..."
    logging.error("❌ JIRA_URL is missing in .env!")

# ==============================================================================
# 🧩 IMPORT GRAPH TOOLS (ที่ต้องการ Environment Variable)
# ==============================================================================
try:
    # Import หลังจาก load_dotenv แล้ว เพื่อให้ Tool อ่านค่าได้ทันที
    from graph.tools.jira import get_jira_ticket
    JIRA_ENABLED = True
except ImportError:
    logging.warning("⚠️ Could not import graph.tools.jira.")
    JIRA_ENABLED = False

try:
    from graph.tools.git_ops import git_push_to_remote, git_status
    GIT_ENABLED = True
except ImportError:
    GIT_ENABLED = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DevAgent")


# ==============================================================================
# 🛡️ SANDBOX WRAPPERS (ตัวกลางดักจับ Path & Logic)
# ==============================================================================

def safe_generate_skeleton(file_path: str) -> str:
    """Wrapper: บังคับอ่านไฟล์จาก Sandbox เท่านั้น"""
    try:
        full_path = os.path.join(AGENT_WORKSPACE, file_path)
        return original_skeleton(full_path)
    except Exception as e:
        return f"Error in skeleton wrapper: {e}"


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
    """⚠️ OVERWRITE file in sandbox."""
    try:
        full_path = os.path.join(AGENT_WORKSPACE, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ File Overwritten: {file_path}"
    except Exception as e:
        return f"Error: {e}"


def append_file(file_path: str, content: str) -> str:
    """✅ APPEND content to file in sandbox."""
    try:
        full_path = os.path.join(AGENT_WORKSPACE, file_path)
        if not os.path.exists(full_path): return f"Error: File not found."
        with open(full_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + content)
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


def git_push_wrapper(branch_name: str) -> str:
    """✅ Pushes the current branch to origin (Sandbox)."""
    try:
        logger.info(f"🚀 Pushing branch {branch_name} to origin...")
        # ใช้ -u origin เพื่อ set upstream
        cmd = f"git push -u origin {branch_name}"
        result = subprocess.run(cmd, shell=True, cwd=AGENT_WORKSPACE, capture_output=True, text=True)

        if result.returncode == 0:
            return f"✅ Push Success: {result.stdout}"
        else:
            return f"❌ Push Failed: {result.stderr}"
    except Exception as e:
        return f"❌ Push Error: {e}"


def create_pr_wrapper(title: str, body: str) -> str:
    """✅ Creates a Pull Request using GitHub CLI (gh) from Sandbox."""
    if not shutil.which("gh"):
        return "❌ Error: GitHub CLI ('gh') is not installed. Please install it first."

    try:
        logger.info(f"🔀 Creating PR: {title}")

        # ดึงชื่อ Branch ปัจจุบัน
        current_branch = subprocess.check_output("git branch --show-current", shell=True, cwd=AGENT_WORKSPACE,
                                                 text=True).strip()

        # คำสั่ง gh pr create
        # --base main (หรือ master แล้วแต่ repo คุณ)
        # --head (branch ปัจจุบัน)
        # --fill (ใช้ title/body จาก commit ถ้าขี้เกียจใส่) แต่เราใส่เองดีกว่า
        cmd = [
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", "main",
            "--head", current_branch
        ]

        # run ใน Sandbox
        result = subprocess.run(
            cmd,
            cwd=AGENT_WORKSPACE,
            capture_output=True,
            text=True,
            shell=True  # Windows บางทีต้องการ shell=True สำหรับ gh
        )

        if result.returncode == 0:
            return f"✅ PR Created Successfully!\nLink: {result.stdout.strip()}"
        elif "already exists" in result.stderr:
            return f"⚠️ PR already exists for this branch.\n{result.stderr}"
        else:
            return f"❌ PR Creation Failed:\n{result.stderr}"

    except Exception as e:
        return f"❌ PR Error: {e}"

def run_unit_test(test_path: str) -> str:
    """
    Runs a unit test file using pytest within the sandbox.
    Returns the Output (stdout) and Errors (stderr).
    """
    try:
        # 1. บังคับ Path ให้อยู่ใน Sandbox
        full_path = os.path.join(AGENT_WORKSPACE, test_path)

        if not os.path.exists(full_path):
            return f"❌ Error: Test file '{test_path}' not found in Sandbox."

        # 2. เตรียมคำสั่ง Run
        command = [sys.executable, "-m", "pytest", full_path]

        # ✅ 3. (FIX) เพิ่ม PYTHONPATH ให้ Python รู้จักโฟลเดอร์ปัจจุบัน (Sandbox Root)
        # เพื่อให้ import src.xxx ทำงานได้
        env = os.environ.copy()
        env["PYTHONPATH"] = AGENT_WORKSPACE + os.pathsep + env.get("PYTHONPATH", "")

        # 4. รันคำสั่ง
        logger.info(f"🧪 Running test: {test_path}...")
        result = subprocess.run(
            command,
            cwd=AGENT_WORKSPACE,  # รันใน Sandbox
            env=env,  # 👈 ส่ง environment ที่แก้แล้วเข้าไป
            capture_output=True,  # จับผลลัพธ์
            text=True  # ขอเป็น String
        )

        # 5. วิเคราะห์ผล
        output = result.stdout + result.stderr

        if result.returncode == 0:
            return f"✅ TESTS PASSED:\n{output}"
        else:
            return f"❌ TESTS FAILED (Exit Code {result.returncode}):\n{output}\n\n👉 INSTRUCTION: Analyze the error above and Fix the code."

    except Exception as e:
        return f"❌ Execution Error: {e}"


# ----------------------------------------------------
# Tools Registration
# ----------------------------------------------------
TOOLS: Dict[str, Any] = {
    # Basic Tools
    "read_jira_ticket": get_jira_ticket,  # (ถ้าเปิด JIRA)
    "init_workspace": init_workspace,
    "list_files": list_files,
    "generate_skeleton": safe_generate_skeleton,
    "read_file": read_file,
    "write_file": write_file,
    "append_file": append_file,

    # QA & Verification Tools
    "run_unit_test": run_unit_test,  # 🧪 หัวใจสำคัญ

    # Git Ops Tools
    "git_commit": git_commit_wrapper,
    "git_push": git_push_wrapper,  # 🚀 เพิ่ม
    "create_pr": create_pr_wrapper,  # 🔀 เพิ่ม
}

# ✅ Register Jira Tool (ถ้า import ผ่าน)
if JIRA_ENABLED:
    # Key คือชื่อที่จะให้ AI เรียก, Value คือฟังก์ชันจาก graph.tools.jira
    TOOLS["read_jira_ticket"] = get_jira_ticket

if GIT_ENABLED:
    TOOLS.update({"git_push": git_push_to_remote, "git_status": git_status})

# ----------------------------------------------------
# System Prompt (The Ultimate Edition: QA Mindset + Delivery)
# ----------------------------------------------------
SYSTEM_PROMPT = """
You are "Beta", an Autonomous AI Developer with a built-in QA mindset.
Your goal is to complete Jira tasks, Verify them with Tests, and Submit a Pull Request.

*** CRITICAL INSTRUCTION: ONE STEP AT A TIME ***
- Output ONLY ONE JSON action per turn.
- WAIT for the tool result before deciding the next step.

*** YOUR STANDARD OPERATING PROCEDURE (SOP) ***
You must follow this workflow automatically for EVERY task:

1. **IMPLICIT TDD RULE (The "Green" Law)**:
   - Whenever you create/modify logic (e.g., `src/foo.py`), you **MUST** create/update `tests/test_foo.py`.
   - Your tests MUST cover:
     - ✅ **Happy Path:** Valid inputs expecting success.
     - ❌ **Edge/Error Cases:** Invalid inputs expecting failures/exceptions.

2. **SELF-HEALING LOOP (The "Repair" Law)**:
   - AFTER writing code & tests, you **MUST** run `run_unit_test`.
   - **IF FAILED**: You are **FORBIDDEN** to commit.
     - Analyze the error log.
     - Fix the source code (or test).
     - Run `run_unit_test` again.
     - Repeat until tests pass (GREEN).

3. **DELIVERY POLICY (The "Ship" Law)**:
   - Only `git_commit` when tests pass.
   - After commit, you MUST `git_push` to origin.
   - Finally, `create_pr` to merge into main.

*** WORKFLOW STEPS (Execute One-by-One) ***
1. **UNDERSTAND**: If a Jira Ticket ID is provided, use read_jira_ticket. Otherwise, skip this step and use the Task Description directly.
2. **INIT**: `init_workspace(branch_name)`.
3. **EXPLORE**: `list_files` / `generate_skeleton`.
4. **CODE**: `write_file` (Source Code).
5. **TEST**: `write_file` (Unit Tests - Positive & Negative cases).
6. **VERIFY**: `run_unit_test` -> Loop Fix if needed.
7. **SAVE**: `git_commit` (Message must be descriptive).
8. **UPLOAD**: `git_push(branch_name)`.
9. **PR**: `create_pr(title, body)`.
   - Body MUST include "Closes [Jira-ID]" and summary.

TOOLS AVAILABLE:
1. read_jira_ticket(issue_key)
2. init_workspace(branch_name)
3. list_files(directory)
4. generate_skeleton(file_path)
5. read_file(file_path)
6. write_file(file_path, content)
7. append_file(file_path, content)
8. run_unit_test(test_path)
9. git_commit(message)
10. git_push(branch_name)
11. create_pr(title, body)
12. task_complete(summary)

RESPONSE FORMAT (JSON ONLY):
{ "action": "tool_name", "args": { ... } }
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
        # ✅ รองรับ LangChain Tool (เช่น get_jira_ticket) ที่ต้องใช้ .invoke()
        if hasattr(func, 'invoke'):
            # LangChain Tools มักรับ Input เป็น dict เดียว หรือ arg แยก
            # กรณี get_jira_ticket ของคุณรับ issue_key: str
            return str(func.invoke(args))
        else:
            # Python Function ปกติ
            return str(func(**args))
    except Exception as e:
        return f"Error executing {tool_name}: {e}"


def run_dev_agent_task(task_description: str, max_steps: int = 30) -> str:
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