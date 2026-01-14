import json
import logging
import re
import subprocess
import os
import sys
import shutil
import time
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


def read_jira_ticket_wrapper(issue_key: str) -> str:
    """Wrapper: เรียก Jira ของจริง แต่ดักจับ Error เพื่อกัน Loop"""
    if not JIRA_ENABLED:
        return "❌ Error: Jira Tool is not configured or failed to import."

    try:
        # เรียก Tool ของจริง (get_jira_ticket มักจะเป็น LangChain Tool ต้องใช้ .invoke)
        # ส่ง input ตาม format ที่ tool นั้นต้องการ (เดาว่ารับ dict หรือ str)
        result = get_jira_ticket.invoke({"issue_key": issue_key})

        result_str = str(result)

        # 🟢 KILL SWITCH: ถ้าหาไม่เจอ ให้ด่ากลับไปเลยว่า "หยุดลอง!"
        if "not found" in result_str.lower() or "404" in result_str:
            return (f"❌ Error: Jira Ticket '{issue_key}' NOT FOUND.\n"
                    f"⚠️ STOP TRYING to read this ticket.\n"
                    f"👉 ACTION: Use the requirements provided by the user in the task description instead.")

        return result_str

    except Exception as e:
        return f"❌ Jira Execution Error: {e}"

def init_workspace(branch_name: str, base_branch: str = "main") -> str:
    """Setup Sandbox: Clone directly from Remote URL -> Config -> Checkout"""
    try:
        # 🟢 STEP 1: หา GitHub URL จาก Main Repo ก่อน
        # (เพื่อให้ไม่ต้อง Hardcode URL ใน Agent)
        try:
            remote_url = subprocess.check_output(
                "git config --get remote.origin.url",
                shell=True,
                cwd=MAIN_REPO_PATH,
                text=True
            ).strip()
            logger.info(f"🔗 Detected Remote URL: {remote_url}")
        except Exception as e:
            return f"❌ Error: Could not detect remote URL from {MAIN_REPO_PATH}. Is it a git repo?"

        # 🟢 STEP 2: Clone จาก GitHub URL ลง Sandbox (Cleanest Way)
        if not os.path.exists(AGENT_WORKSPACE):
            logger.info(f"📂 Creating Sandbox at: {AGENT_WORKSPACE}")
            os.makedirs(AGENT_WORKSPACE, exist_ok=True)

            # Clone ตรงจาก GitHub (ใช้ Auth ที่เรา Setup ไว้)
            logger.info(f"⬇️ Cloning from {remote_url}...")
            subprocess.run(f'git clone "{remote_url}" .', shell=True, cwd=AGENT_WORKSPACE, check=True)

        os.chdir(AGENT_WORKSPACE)

        # ไม่ต้อง set-url แล้ว เพราะ Clone มาจากของจริง Origin ก็จะเป็นของจริงอัตโนมัติ ✅

        # Config User Agent
        subprocess.run('git config user.name "AI Dev Agent"', shell=True, cwd=AGENT_WORKSPACE, check=True)
        subprocess.run('git config user.email "ai_agent@local.dev"', shell=True, cwd=AGENT_WORKSPACE, check=True)

        # Checkout Flow
        subprocess.run(f"git fetch origin", shell=True, cwd=AGENT_WORKSPACE, check=True, capture_output=True)

        # Checkout Base Branch (main) ให้ชัวร์ก่อน
        subprocess.run(f"git checkout {base_branch}", shell=True, cwd=AGENT_WORKSPACE, check=True, capture_output=True)
        subprocess.run(f"git pull origin {base_branch}", shell=True, cwd=AGENT_WORKSPACE, capture_output=True)

        # Create Feature Branch
        subprocess.run(f"git checkout -B {branch_name}", shell=True, cwd=AGENT_WORKSPACE, check=True,
                       capture_output=True)

        return f"✅ Sandbox Ready: Branch '{branch_name}' created from remote '{base_branch}'."

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

        # Check Commits
        has_commits = subprocess.run("git rev-parse --verify HEAD", shell=True, cwd=AGENT_WORKSPACE,
                                     capture_output=True)
        if has_commits.returncode != 0:
            return "❌ Push Failed: No commits yet."

        # Push Command
        cmd = f"git push -u origin {branch_name}"

        # ✅ เพิ่ม env เพื่อบังคับใช้ gh เป็น credential helper (กันเหนียว)
        env = os.environ.copy()
        # env["GCM_CREDENTIAL_STORE"] = "cache" # Optional

        result = subprocess.run(cmd, shell=True, cwd=AGENT_WORKSPACE, capture_output=True, text=True, env=env)

        if result.returncode == 0:
            return f"✅ Push Success: {result.stdout}"
        else:
            error_msg = result.stderr
            # 🕵️‍♂️ ดักจับ Authentication Error
            if "403" in error_msg or "Authentication failed" in error_msg or "logon failed" in error_msg:
                return f"❌ AUTH ERROR: Git cannot authenticate. Please run 'gh auth setup-git' on the host machine.\nDetails: {error_msg}"

            if "does not match any" in error_msg:
                return f"❌ Push Failed: Branch missing. Commit first?"

            return f"❌ Push Failed: {error_msg}"

    except Exception as e:
        return f"❌ Push Error: {e}"


def git_pull_wrapper(branch_name: str = "main") -> str:
    """✅ Pulls latest changes from remote to Sandbox."""
    try:
        logger.info(f"⬇️ Pulling from origin/{branch_name}...")

        # ใช้ Environment เดิมที่มีอยู่
        env = os.environ.copy()

        # สั่ง git pull ใน Sandbox (AGENT_WORKSPACE)
        cmd = f"git pull origin {branch_name} --no-rebase"

        result = subprocess.run(
            cmd,
            shell=True,
            cwd=AGENT_WORKSPACE,  # 👈 สำคัญมาก! ต้องระบุ Sandbox Path
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode == 0:
            return f"✅ Pull Success:\n{result.stdout}"
        else:
            return f"❌ Pull Failed:\n{result.stderr}"

    except Exception as e:
        return f"❌ Pull Error: {e}"

def create_pr_wrapper(title: str, body: str) -> str:
    """✅ Creates a Pull Request using GitHub CLI (gh) from Sandbox."""
    if not shutil.which("gh"):
        return "❌ Error: GitHub CLI ('gh') is not installed."

    try:
        logger.info(f"🔀 Creating PR: {title}")

        # 1. รอสักนิดเพื่อให้ GitHub Server รู้ตัวว่ามี Branch ใหม่มาแล้ว
        time.sleep(3)

        # ดึงชื่อ Branch ปัจจุบัน
        current_branch = subprocess.check_output("git branch --show-current", shell=True, cwd=AGENT_WORKSPACE,
                                                 text=True).strip()

        # คำสั่ง gh pr create
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
            shell=True
        )

        if result.returncode == 0:
            return f"✅ PR Created Successfully!\nLink: {result.stdout.strip()}"

        # 🟢 แก้ไข: ถ้ามี PR อยู่แล้ว ให้ถือว่าผ่าน! (AI จะได้ไม่วนลูป)
        elif "already exists" in result.stderr:
            # พยายามดึง Link จาก Error Message (GitHub มักจะบอก URL มาด้วย)
            return f"✅ PR Success (Already Exists): {result.stderr.strip()}"

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


def install_package_wrapper(package_name: str) -> str:
    """✅ Installs a Python package using pip in the current venv."""
    try:
        # ป้องกันการติดตั้ง package อันตราย หรือการพิมพ์ผิด
        if any(char in package_name for char in [";", "&", "|", ">"]):
            return "❌ Error: Invalid package name."

        logger.info(f"📦 Installing package: {package_name}...")

        # รัน pip install
        command = [sys.executable, "-m", "pip", "install", package_name]

        result = subprocess.run(
            command,
            cwd=AGENT_WORKSPACE,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return f"✅ Installed '{package_name}' successfully."
        else:
            return f"❌ Install Failed:\n{result.stderr}"

    except Exception as e:
        return f"❌ System Error: {e}"

# ----------------------------------------------------
# Tools Registration
# ----------------------------------------------------
TOOLS: Dict[str, Any] = {
    # Basic Tools
    # "read_jira_ticket": get_jira_ticket,  # (ถ้าเปิด JIRA)
    "init_workspace": init_workspace,
    "list_files": list_files,
    "generate_skeleton": safe_generate_skeleton,
    "read_file": read_file,
    "write_file": write_file,
    "append_file": append_file,
    "install_package": install_package_wrapper, # 👈 เพิ่มบรรทัดนี้

    # QA & Verification Tools
    "run_unit_test": run_unit_test,  # 🧪 หัวใจสำคัญ

    # Git Ops Tools
    "git_commit": git_commit_wrapper,
    "git_push": git_push_wrapper,  # 🚀 เพิ่ม
    "git_pull": git_pull_wrapper,
    "create_pr": create_pr_wrapper,  # 🔀 เพิ่ม
}

# ✅ Register Jira Tool (ถ้า import ผ่าน)
if JIRA_ENABLED:
    TOOLS["read_jira_ticket"] = read_jira_ticket_wrapper

if GIT_ENABLED:
    TOOLS.update({"git_status": git_status})

# ----------------------------------------------------
# System Prompt (The Ultimate Edition: QA Mindset + Delivery)
# ----------------------------------------------------
SYSTEM_PROMPT = """
You are "Beta", an Autonomous AI Developer with a built-in QA mindset.
Your goal is to complete Jira tasks, Verify them with Tests, and Submit a Pull Request.

*** CRITICAL INSTRUCTION: ONE STEP AT A TIME ***
- Output **ONLY ONE** JSON action per turn.
- **NEVER** chain multiple JSON blocks.
- **NO COMMENTS IN JSON**: Do not use // or # inside the JSON block.

*** ACTION OVER CHAT (CRITICAL) ***
- **DO NOT** output code blocks in the chat/explanation text.
- If you need to write or fix code, you **MUST** use the `write_file` tool.
- Explanation is NOT implementation. You can only affect the file system via tools.

*** JSON FORMATTING RULES (STRICT) ***
1. **NO COMMENTS**: Do not use // or # inside the JSON block.
2. **ESCAPE NEWLINES**: When writing file content, you MUST escape newlines as `\\n`. Do NOT put actual line breaks inside the JSON string value.
3. **SIMPLE DOCSTRINGS**: Avoid complex multi-line docstrings if possible to prevent JSON parsing errors.

*** CODING STANDARDS ***
1. **ABSOLUTE IMPORTS ONLY**: Always use `from src.utils.math_ops import ...`. **NEVER** use relative imports like `from ..math_ops`.
2. **TEST LOCATION**: Always place tests in `tests/` folder (e.g., `tests/test_math_ops.py`), NOT in `src/`.

*** PYTHON IMPORT RULES (CRITICAL) ***
1. PROJECT STRUCTURE:
   - Source code is ALWAYS in `src/` folder (e.g., `src/main.py`).
   - Tests are in `tests/` folder.
2. IMPORT PATHS:
   - When importing code from `tests/`, you MUST use absolute imports with `src.` prefix.
   - ❌ WRONG: `from main import app`
   - ✅ RIGHT: `from src.main import app`
3. TROUBLESHOOTING IMPORT ERRORS:
   - If you get `ModuleNotFoundError: No module named 'main'`, it means you forgot the `src.` prefix.
   - FIX IT by changing the import in the TEST file, NOT by moving the source file.

*** YOUR STANDARD OPERATING PROCEDURE (SOP) ***
You must follow this workflow automatically for EVERY task:

*** ERROR HANDLING STRATEGY (CRITICAL) ***
When you encounter `ModuleNotFoundError: No module named 'X'`:

1. **ANALYZE the name 'X'**:
   - Is it a generic library name (e.g., `requests`, `pandas`, `httpx`, `pytest`)?
   - OR is it a project-specific path (e.g., `src.models`, `utils.helpers`, `main`)?

2. **EXECUTE the correct fix**:
   - **CASE A: External Library (e.g., 'httpx')**
     -> DO NOT create a file named 'httpx.py'.
     -> ACTION: Call `install_package('httpx')`.
     -> THEN: Add it to `requirements.txt` using `append_file`.

   - **CASE B: Internal Project Code (e.g., 'src.utils.math')**
     -> DO NOT modify the test file yet.
     -> ACTION: Call `write_file` to CREATE the missing implementation file at `src/utils/math.py`.
     -> THEN: Retry the test.

1. **IMPLICIT TDD RULE**:
   - Whenever you create/modify logic, you MUST create/update tests.
   - Tests MUST cover Positive & Negative cases.

2. **SELF-HEALING LOOP**:
   - Run `run_unit_test`.
   - IF FAILED: Fix code/test -> Retry.
   - You are FORBIDDEN to commit if tests fail.

3. **DELIVERY POLICY**:
   - Only `git_commit` when tests pass.
   - **CRITICAL:** `git_push` MUST be done on the **Current Feature Branch** (NOT 'main').
   - After `create_pr` returns a success link, you **MUST** immediately call `task_complete`.

*** WORKFLOW STEPS (Execute One-by-One) ***
*** CONSISTENCY RULE: *** Once you define `branch_name` in Step 2, you MUST use EXACTLY the same name for all future git operations (push/pull). DO NOT create or switch to new branch names mid-task.

1. **UNDERSTAND**: Read Task (or Jira).
2. **INIT**: `init_workspace(branch_name)`.
3. **EXPLORE**: `list_files` / `generate_skeleton`.
4. **CODE**: `write_file` (Source Code).
5. **TEST**: `write_file` (Unit Tests).
6. **VERIFY**: `run_unit_test` -> Loop Fix.
7. **SAVE**: `git_commit`.
8. **UPLOAD**: `git_push(branch_name)` <--- ⚠️ CRITICAL: MUST be exact match of Step 2.
9. **PR**: `create_pr`.
10. **FINISH**: `task_complete`.

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
11. git_pull(branch_name)
12. create_pr(title, body)
13. task_complete(summary)
14. install_package(package_name)

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

    # Init History
    history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task_description}"}
    ]

    for step in range(max_steps):
        logger.info(f"🔄 Step {step + 1}/{max_steps}...")

        # ----------------------------------------
        # 1. ส่งให้ AI คิด (ใช้ query_qwen ที่ import มา)
        # ----------------------------------------
        # ⚠️ แก้ตรงนี้: ใช้ query_qwen และส่ง history เข้าไป
        try:
            # สมมติว่า query_qwen รับ list of messages และ return content string หรือ dict
            # ปรับตาม implementation จริงของ local_agent.llm_client
            response_payload = query_qwen(history)

            # ถ้า query_qwen return dict ให้ดึง content ออกมา
            if isinstance(response_payload, dict):
                content = response_payload.get('message', {}).get('content', '') or response_payload.get('content', '')
            else:
                content = str(response_payload)

        except Exception as e:
            logger.error(f"❌ LLM Error: {e}")
            return f"LLM Error: {e}"

        print(f"🤖 AI Raw Output: {content}")  # Debug

        # # ----------------------------------------
        # # 2. กรอง JSON (Safety Filter)
        # # ----------------------------------------
        # # พยายามหา Block ```json ... ``` อันแรกสุด
        # json_matches = re.findall(r"```json(.*?)```", content, re.DOTALL)
        #
        # if json_matches:
        #     # ✅ เจอ JSON! เอาแค่อันแรก (Index 0) - ตัดส่วนเกินทิ้ง
        #     clean_content = json_matches[0].strip()
        #     if len(json_matches) > 1:
        #         logger.warning(f"⚠️ AI sent {len(json_matches)} actions. IGNORING extras to prevent loops.")
        # else:
        #     # กรณีไม่ใส่ Markdown หา { } อันแรก
        #     brace_matches = re.search(r"\{.*\}", content, re.DOTALL)
        #     if brace_matches:
        #         clean_content = brace_matches.group(0).strip()
        #     else:
        #         clean_content = content

        tool_calls = _extract_all_jsons(content)

        # ----------------------------------------
        # 3. Execute Tool
        # ----------------------------------------
        if not tool_calls:
            logger.warning("msg: No valid JSON found, treating as thought.")
            history.append({"role": "assistant", "content": content})
            continue

        step_outputs = []
        task_finished = False

        # Loop นี้จะรันครบทุก Action ที่ AI ส่งมา (เช่น เขียนเสร็จ -> รันเทสต่อเลย)
        for tool_call in tool_calls:
            action = tool_call.get("action")
            args = tool_call.get("args", {})

            if action == "task_complete":
                task_finished = True
                result = args.get("summary", "Done")
                # ถ้าจบงานแล้ว break เลย ไม่ต้องทำ action ต่อไป (ถ้ามี)
                step_outputs.append(f"Task Completed: {result}")
                break

            logger.info(f"🔧 Executing Tool: {action}")
            result = execute_tool_dynamic(action, args)
            step_outputs.append(f"Tool Output ({action}):\n{result}")

            # Safety Break for Init Failure
            if action == "init_workspace" and "❌" in result:
                return f"FAILED: {result}"

        if task_finished:
            print(f"\n✅ TASK COMPLETED: {result}")
            return "SUCCESS"

        # ----------------------------------------
        # 4. Update History
        # ----------------------------------------
        combined_output = "\n".join(step_outputs)

        # เก็บสิ่งที่ AI ตอบ (clean หรือ raw ก็ได้ แต่ raw ดีกว่าสำหรับ debug context)
        history.append({"role": "assistant", "content": content})

        # เก็บผลลัพธ์จาก Tool ส่งกลับไปให้ AI รู้
        history.append({"role": "user", "content": combined_output})

    return "❌ FAILED: Max steps reached."