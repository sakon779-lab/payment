import json
import logging
import re
import subprocess
import os
import sys
import shutil
import time
import base64
import requests
import ast
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Import LLM Client
try:
    from local_agent.llm_client import query_qwen
except ImportError:
    def query_qwen(history):
        print("❌ Error: Missing local_agent.llm_client")
        return "{}"

# ==============================================================================
# 📍 CONFIGURATION
# ==============================================================================
MAIN_REPO_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_WORKSPACE = r"D:\WorkSpace\QaAutomationAgent"
QA_REPO_URL = "https://github.com/sakon779-lab/qa-automation-repo.git"

# ==============================================================================
# 🔑 SECURITY & ENVIRONMENT SETUP
# ==============================================================================
env_path = os.path.join(MAIN_REPO_PATH, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    logging.info(f"✅ Loaded environment variables from: {env_path}")

JIRA_BASE_URL = os.getenv("JIRA_URL")
JIRA_USER_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("QAAgent")


# ==============================================================================
# 🛡️ SANDBOX WRAPPERS
# ==============================================================================
def list_files(directory: str = ".") -> str:
    try:
        target_dir = os.path.join(AGENT_WORKSPACE, directory) if directory != "." else AGENT_WORKSPACE
        files = []
        for root, _, filenames in os.walk(target_dir):
            if ".git" in root or ".venv" in root or "results" in root: continue
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), AGENT_WORKSPACE)
                files.append(rel_path)
        if not files: return "No files found."
        files.sort()
        return f"📂 Project Structure ({len(files)} files):\n" + "\n".join(files[:50])
    except Exception as e:
        return f"Error: {e}"


def read_file(file_path: str) -> str:
    try:
        full_path = os.path.join(AGENT_WORKSPACE, file_path)
        if not os.path.exists(full_path): return f"Error: File not found."
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"


def write_file(file_path: str, content: str) -> str:
    try:
        full_path = os.path.join(AGENT_WORKSPACE, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ File Written: {file_path}"
    except Exception as e:
        return f"Error: {e}"


def append_file(file_path: str, content: str) -> str:
    try:
        full_path = os.path.join(AGENT_WORKSPACE, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "a", encoding="utf-8") as f:
            f.write("\n\n" + content)
        return f"✅ Appended to: {file_path}"
    except Exception as e:
        return f"Error: {e}"


def read_jira_ticket(issue_key: str) -> str:
    logger.info(f"🔍 Fetching Jira Ticket: {issue_key}...")
    if not JIRA_USER_EMAIL or not JIRA_API_TOKEN or not JIRA_BASE_URL:
        return "⚠️ Jira Config Missing in .env! Please interpret requirements from user input."

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"
    auth_str = f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}"
    auth_base64 = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {auth_base64}", "Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            fields = data.get('fields', {})
            return (
                f"TICKET: {issue_key}\nSUMMARY: {fields.get('summary')}\nDESC: {json.dumps(fields.get('description'))}")
        return f"❌ Ticket {issue_key} not found."
    except Exception as e:
        return f"❌ Connection Error: {e}"


# ==============================================================================
# 🛡️ GIT OPS
# ==============================================================================
def init_workspace(branch_name: str, base_branch: str = "main") -> str:
    try:
        if not os.path.exists(os.path.join(AGENT_WORKSPACE, ".git")):
            logger.info(f"📂 Creating QA Sandbox at: {AGENT_WORKSPACE}")
            os.makedirs(AGENT_WORKSPACE, exist_ok=True)
            logger.info(f"⬇️ Cloning from {QA_REPO_URL}...")
            subprocess.run(f'git clone "{QA_REPO_URL}" .', shell=True, cwd=AGENT_WORKSPACE, check=True)

        subprocess.run('git config user.name "AI QA Agent"', shell=True, cwd=AGENT_WORKSPACE, check=True)
        subprocess.run('git config user.email "qa_agent@local.dev"', shell=True, cwd=AGENT_WORKSPACE, check=True)

        logger.info(f"🔄 Syncing with origin/{base_branch}...")
        subprocess.run(f"git fetch origin", shell=True, cwd=AGENT_WORKSPACE, check=True, capture_output=True)
        subprocess.run(f"git checkout {base_branch}", shell=True, cwd=AGENT_WORKSPACE, check=True, capture_output=True)
        subprocess.run(f"git pull origin {base_branch}", shell=True, cwd=AGENT_WORKSPACE, capture_output=True)

        logger.info(f"🌿 Switching to branch: {branch_name}")
        subprocess.run(f"git checkout -B {branch_name}", shell=True, cwd=AGENT_WORKSPACE, check=True,
                       capture_output=True)
        return f"✅ QA Workspace Ready: Branch '{branch_name}'."
    except Exception as e:
        return f"❌ Init failed: {e}"


def git_commit_wrapper(message: str) -> str:
    try:
        current_branch = subprocess.check_output("git branch --show-current", shell=True, cwd=AGENT_WORKSPACE,
                                                 text=True).strip()
        status = subprocess.check_output("git status --porcelain", shell=True, cwd=AGENT_WORKSPACE, text=True)
        if not status: return f"⚠️ Nothing to commit on '{current_branch}'. Proceed to push."
        subprocess.run("git add .", shell=True, cwd=AGENT_WORKSPACE, check=True)
        result = subprocess.run(f'git commit -m "{message}"', shell=True, cwd=AGENT_WORKSPACE, capture_output=True,
                                text=True)
        if result.returncode == 0: return f"✅ Commit Success on '{current_branch}': {message}"
        return f"❌ Commit Failed: {result.stderr}"
    except Exception as e:
        return f"❌ Git Error: {e}"


def git_push_wrapper(branch_name: str) -> str:
    try:
        current_branch = subprocess.check_output("git branch --show-current", shell=True, cwd=AGENT_WORKSPACE,
                                                 text=True).strip()
        if branch_name != current_branch: return f"❌ CONTEXT ERROR: You are on '{current_branch}' but tried to push '{branch_name}'."
        cmd = f"git push -u origin {branch_name}"
        env = os.environ.copy()
        result = subprocess.run(cmd, shell=True, cwd=AGENT_WORKSPACE, capture_output=True, text=True, env=env)
        if result.returncode == 0: return f"✅ Push Success: {branch_name}"
        return f"❌ Push Failed: {result.stderr}"
    except Exception as e:
        return f"❌ Push Error: {e}"


def create_pr_wrapper(title: str, body: str) -> str:
    if not shutil.which("gh"): return "❌ Error: GitHub CLI ('gh') not installed."
    try:
        current_branch = subprocess.check_output("git branch --show-current", shell=True, cwd=AGENT_WORKSPACE,
                                                 text=True).strip()
        cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--base", "main", "--head", current_branch]
        result = subprocess.run(cmd, cwd=AGENT_WORKSPACE, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            return f"✅ PR Created: {result.stdout.strip()}"
        elif "already exists" in result.stderr:
            return f"✅ PR Already Exists."
        return f"❌ PR Failed: {result.stderr}"
    except Exception as e:
        return f"❌ PR Error: {e}"


# ==============================================================================
# 🧪 TEST TOOLS (Robot Framework)
# ==============================================================================
def run_robot_test(file_path: str) -> str:  # 👈 แก้ชื่อตัวแปรตรงนี้จาก test_path เป็น file_path
    """Runs a Robot Framework test file."""
    try:
        # แก้ตรงนี้ด้วยให้ใช้ variable ใหม่
        full_path = os.path.join(AGENT_WORKSPACE, file_path)

        if not os.path.exists(full_path):
            return f"❌ Error: Test file '{file_path}' not found."  # 👈 แก้ตรงนี้

        results_dir = os.path.join(AGENT_WORKSPACE, "results")
        os.makedirs(results_dir, exist_ok=True)

        command = [sys.executable, "-m", "robot", "-d", "results", full_path]
        logger.info(f"🤖 Running Robot Test: {file_path}...")  # 👈 แก้ตรงนี้

        env = os.environ.copy()
        env["PYTHONPATH"] = AGENT_WORKSPACE + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(command, cwd=AGENT_WORKSPACE, env=env, capture_output=True, text=True)
        output = result.stdout + "\n" + result.stderr

        if result.returncode == 0:
            return f"✅ ROBOT PASSED:\n{output}"
        else:
            return f"❌ ROBOT FAILED (Exit Code {result.returncode}):\n{output}\n\n👉 INSTRUCTION: Analyze the failure logs above and fix the .robot file."

    except Exception as e:
        return f"❌ Execution Error: {e}"


def install_package_wrapper(package_name: str) -> str:
    try:
        logger.info(f"📦 Installing: {package_name}...")
        command = [sys.executable, "-m", "pip", "install", package_name]
        result = subprocess.run(command, cwd=AGENT_WORKSPACE, capture_output=True, text=True)
        if result.returncode == 0: return f"✅ Installed '{package_name}'."
        return f"❌ Install Failed: {result.stderr}"
    except Exception as e:
        return f"❌ Error: {e}"


def run_shell_command(command: str) -> str:
    try:
        logger.info(f"💻 Shell: {command}")
        result = subprocess.run(command, shell=True, cwd=AGENT_WORKSPACE, capture_output=True, text=True)
        return f"Output:\n{result.stdout}\n{result.stderr}"
    except Exception as e:
        return f"Error: {e}"


TOOLS: Dict[str, Any] = {
    "read_jira_ticket": read_jira_ticket, "init_workspace": init_workspace,
    "list_files": list_files, "read_file": read_file, "write_file": write_file,
    "append_file": append_file, "run_robot_test": run_robot_test, "run_shell_command": run_shell_command,
    "install_package": install_package_wrapper, "git_commit": git_commit_wrapper,
    "git_push": git_push_wrapper, "create_pr": create_pr_wrapper
}

# ==============================================================================
# 🧠 SYSTEM PROMPT (Gamma Persona - Enhanced Logic)
# ==============================================================================
SYSTEM_PROMPT = """
You are "Gamma", a Senior QA Automation Engineer (Robot Framework Expert).
Your goal is to Create, Verify, and Deliver automated tests autonomously.

*** CRITICAL: ATOMICITY & FORMAT ***
1. **ONE ACTION PER TURN**: Strictly ONE JSON block per response.
2. **NO CHAINING**: Wait for the tool result.
3. **STOP**: Stop after `}`.

*** SCOPE FILTERING (CRITICAL) ***
1. **IGNORE UNIT TEST INSTRUCTIONS**:
   - The Jira ticket describes tasks for Developers (e.g., "Create src/main.py", "Write tests/test_api.py using pytest").
   - **DO NOT** implement Python Unit Tests or Source Code.
   - **DO NOT** create files like `tests/test_api.py` inside the QA Repository.
2. **TRANSLATE TO ROBOT**:
   - Instead, READ the Requirement to understand the *Behavior*.
   - Example: If Jira says "Unit test must check status 200", you MUST implement a **Robot Framework test** that checks status 200.

*** 🧠 INTELLIGENT BEHAVIOR (DO NOT WAIT FOR INSTRUCTIONS) ***
1. **DISCOVER STRUCTURE**:
   - Before creating any file, use `list_files` to understand the existing folder structure.
   - If `tests/payment_service/` exists, put new payment tests there. DO NOT create `tests/api/` if it breaks consistency.
2. **DESIGN TEST SCENARIOS**:
   - Do NOT just test the "Happy Path".
   - AUTOMATICALLY generate:
     - 1. Positive Case (200 OK)
     - 2. Negative Case (Validation errors, 400/404)
     - 3. Edge Case (Empty strings, Special chars, Boundary values)
3. **SELF-CORRECTION**:
   - If a test fails, analyze the log. If it's a script error, FIX IT. If it's a bug, REPORT IT.

*** IMPORTANT: JSON STRING FORMATTING ***
- Do NOT use triple quotes (\"\"\") for strings in JSON. This is invalid JSON.
- For multi-line file content, use `\\n` to escape newlines.

*** ROBOT FRAMEWORK SYNTAX RULES (STRICT) ***
1. **HEADERS**: ALWAYS use 3 asterisks.
   - Correct: `*** Settings ***`, `*** Test Cases ***`, `*** Variables ***`
   - Wrong: `** Settings **` (2 asterisks will FAIL).
2. **SEPARATORS**: Use **4 SPACES** (or `\\t`) between keywords and arguments.
   - Correct: `Create Session    mysession    http://localhost:8080`
   - Wrong: `Create Session mysession http://localhost:8080` (Single space will FAIL).
3. **DICTIONARY ACCESS**:
   - Use `${response.json()}[key]` syntax for modern Robot, or `Get From Dictionary` from `Collections`.

*** ERROR HANDLING STRATEGY (ONLY FOR FAILED TESTS) ***
IF AND ONLY IF `run_robot_test` fails (returns ❌), analyze the error message:
(Do NOT treat Jira Requirements or Success messages as errors!)

1. **SCRIPT ERRORS (Self-Healing Target)**:
   - IF error contains: `No keyword with name`, `Variable ... not found`, `ImportError`, `invalid syntax`
   - **ACTION**: These are YOUR mistakes. **FIX the .robot file**.
   - *Example*: If `No keyword 'Get From Dictionary'`, ADD `Library Collections` to Settings.

2. **ASSERTION FAILURES (Potential Bugs)**:
   - IF error contains: `should be ... but was ...`, `Status should be 200`, `Dictionary does not contain key`
   - **ACTION**: 
     - First, DOUBLE CHECK your test logic. Did you expect the wrong thing?
     - If you are following the Requirement correctly, **DO NOT CHANGE THE TEST** to match the wrong output.
     - instead, **STOP and REPORT** that a potential BUG was found.

*** QA CODING STANDARDS ***
1. **ISOLATION**: Use `${uuid}` or Random Strings. Use `[Setup]` / `[Teardown]`.
2. **STRUCTURE**: Tests in `tests/project/`.
3. **LIBRARIES**: 
   - ALWAYS `Library RequestsLibrary`.
   - ALWAYS `Library Collections` (if using Dictionaries/JSON).
   - ALWAYS `Library String`.

*** WORKFLOW ***
1. **UNDERSTAND**: `read_jira_ticket` (if provided) or prompt.
2. **INIT**: `init_workspace(branch_name)` (prefix `qa/`).
3. **PLAN & CODE**: `write_file` (.robot).
4. **VERIFY**: `run_robot_test` -> **Apply Error Handling Strategy**.
5. **DELIVERY**: `git_commit` (Only if pass) -> `git_push` -> `create_pr` -> `task_complete`.

TOOLS AVAILABLE:
read_jira_ticket(issue_key), 
init_workspace(branch_name), 
list_files(directory), 
read_file(file_path), 
write_file(file_path, content), 
append_file(file_path, content),
run_robot_test(file_path),  <-- ระบุชัดๆ แบบนี้เลย
git_commit(message), 
git_push(branch_name), 
create_pr(title, body), 
install_package(package_name), 
task_complete(summary), 
run_shell_command(command)

RESPONSE FORMAT (JSON ONLY):
{ "action": "tool_name", "args": { ... } }
"""


# ==============================================================================
# 🧩 ROBUST JSON EXTRACTION (The Fix!)
# ==============================================================================
def _extract_all_jsons(text: str) -> List[Dict[str, Any]]:
    """
    Extracts JSON actions.
    FEATURE: Supports Python-style dicts with triple quotes (common LLM error).
    """
    results = []

    # 1. Try Standard JSON Decoding first (Fast path)
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

    # 2. If Standard JSON failed, Try Python AST (The 'Dirty' Fix)
    if not results:
        try:
            # Find the largest block that looks like a dict { ... }
            matches = re.findall(r"(\{.*?\})", text, re.DOTALL)
            for match in matches:
                try:
                    # Clean up common JSON-isms that break python AST
                    clean_match = match.replace("true", "True").replace("false", "False").replace("null", "None")
                    obj = ast.literal_eval(clean_match)
                    if isinstance(obj, dict) and "action" in obj:
                        results.append(obj)
                except:
                    continue
        except:
            pass

    return results


def execute_tool_dynamic(tool_name: str, args: Dict[str, Any]) -> str:
    if tool_name not in TOOLS: return f"Error: Unknown tool '{tool_name}'"
    try:
        func = TOOLS[tool_name]
        return str(func(**args))
    except Exception as e:
        return f"Error executing {tool_name}: {e}"


def run_qa_agent_task(task_description: str, max_steps: int = 30) -> str:
    logger.info(f"🚀 Starting QA Task: {task_description}")

    history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task_description}"}
    ]

    for step in range(max_steps):
        logger.info(f"🔄 Step {step + 1}/{max_steps}...")

        try:
            response_payload = query_qwen(history)
            if isinstance(response_payload, dict):
                content = response_payload.get('message', {}).get('content', '') or response_payload.get('content', '')
            else:
                content = str(response_payload)
        except Exception as e:
            logger.error(f"❌ LLM Error: {e}")
            return f"LLM Error: {e}"

        print(f"🤖 AI Output: {content[:100]}...")

        tool_calls = _extract_all_jsons(content)

        if not tool_calls:
            logger.warning("No valid JSON found, treating as thought.")
            history.append({"role": "assistant", "content": content})
            continue

        step_outputs = []
        task_finished = False

        for tool_call in tool_calls:
            action = tool_call.get("action")
            args = tool_call.get("args", {})

            # 🔥 FIX: ถ้า AI ส่ง JSON มาแต่ไม่มี Action (คือการสรุปงาน/คิด)
            if not action:
                logger.info("🤔 AI is summarizing/thinking...")
                # แจ้งเตือนกลับไปให้น้องรู้ตัวว่าต้องส่ง Action นะ
                step_outputs.append(
                    "System: You sent a JSON summary but NO 'action'. Please immediately output the next Tool Action JSON (e.g., init_workspace).")
                continue

            if action == "task_complete":
                task_finished = True
                result = args.get("summary", "Done")
                step_outputs.append(f"Task Completed: {result}")
                break

            logger.info(f"🔧 Tool: {action}")
            result = execute_tool_dynamic(action, args)
            step_outputs.append(f"Tool Output ({action}):\n{result}")

            if action == "init_workspace" and "❌" in result:
                return f"FAILED: {result}"

        if task_finished:
            print(f"\n✅ TASK COMPLETED: {result}")
            return result

        history.append({"role": "assistant", "content": content})
        history.append({"role": "user", "content": "\n".join(step_outputs)})

    return "❌ FAILED: Max steps reached."