import os
import subprocess
import json
import requests
import base64
import sys


# ==============================================================================
# 🛠️ ENV LOADER & CONFIG
# ==============================================================================
def load_env():
    """Loads environment variables from a .env file in the parent directory."""
    # หา .env ที่ root folder (ถอยออกมา 1 ชั้นจาก local_agent)
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip("'").strip('"')


load_env()

TARGET_REPO_PATH = r"D:\WorkSpace\QaAutomationAgent"
QA_REPO_URL = "https://github.com/sakon779-lab/qa-automation-repo.git"
OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5-coder:14b"

# Jira Config
JIRA_BASE_URL = os.getenv("JIRA_URL")
JIRA_USER_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# ==============================================================================
# 🧠 SYSTEM PROMPT
# ==============================================================================
SYSTEM_PROMPT = f"""
You are "Gamma", a Senior QA Automation Engineer.
You operate on a separate repository located at: `{TARGET_REPO_PATH}`

Your goal is to manage the **QA Automation Repository** (Robot Framework).

*** WORKFLOW (STRICT ORDER) ***
1. **ANALYZE**: If User provides a Ticket ID, use `read_jira_ticket`.
2. **INIT**: `init_workspace(branch_name)`.
3. **PLAN & CODE**: Plan Isolation (`${{uuid}}`) and Mocking. `write_file` tests.
4. **VERIFY**: `run_shell_command("robot ...")` (ALWAYS Run locally).
5. **DELIVERY**: `git_commit`, `git_push`.

TOOLS AVAILABLE:
read_jira_ticket, init_workspace, git_checkout, git_pull, write_file, 
read_file, run_shell_command, list_files, git_commit, git_push

RESPONSE FORMAT (JSON ONLY):
{{ "action": "tool_name", "args": {{ ... }} }}
"""


# ==============================================================================
# 🛠️ TOOLS IMPLEMENTATION
# ==============================================================================
def run_shell_command(command: str, cwd: str = None) -> str:
    work_dir = cwd if cwd else TARGET_REPO_PATH
    if command.startswith("robot") and work_dir == TARGET_REPO_PATH:
        os.makedirs(os.path.join(work_dir, "results"), exist_ok=True)
        if "--outputdir" not in command: command = f"{command} --outputdir results"

    print(f"💻 Executing in '{work_dir}': {command}")
    try:
        result = subprocess.run(command, shell=True, cwd=work_dir, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + "\n" + result.stderr
        return f"Output:\n{output}" if result.returncode == 0 else f"❌ Failed:\n{output}"
    except Exception as e:
        return f"❌ Error: {e}"


def read_jira_ticket(issue_key: str) -> str:
    print(f"🔍 Fetching Jira Ticket: {issue_key}...")
    if not JIRA_USER_EMAIL or not JIRA_API_TOKEN or not JIRA_BASE_URL:
        return "⚠️ Jira Config Missing in .env! Please provide details manually."

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"
    auth_str = f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}"
    auth_base64 = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {auth_base64}", "Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            fields = data.get('fields', {})
            return f"TICKET: {issue_key}\nSUMMARY: {fields.get('summary')}\nDESC: {json.dumps(fields.get('description'))}"
        return f"❌ Ticket {issue_key} not found."
    except Exception as e:
        return f"❌ Connection Error: {e}"


def git_action(action, **kwargs):
    # Simplified wrapper for git tools to keep code short
    cmd = ""
    if action == "clone":
        if os.path.exists(os.path.join(TARGET_REPO_PATH, ".git")): return "✅ Repo exists."
        os.makedirs(TARGET_REPO_PATH, exist_ok=True)
        cmd = f"git clone {QA_REPO_URL} ."
    elif action == "status":
        cmd = "git status --porcelain"
    elif action == "pull":
        cmd = f"git pull origin {kwargs.get('branch', 'main')}"
    elif action == "checkout":
        branch = kwargs.get('branch')
        res = run_shell_command(f"git checkout {branch}")
        if "error" in res.lower() and kwargs.get('new', False):
            cmd = f"git checkout -b {branch}"
        else:
            return res
    elif action == "commit":
        run_shell_command("git add .")
        cmd = f'git commit -m "{kwargs.get("message")}"'
    elif action == "push":
        cmd = f"git push origin {kwargs.get('branch')}"

    if cmd: return run_shell_command(cmd)
    return "❌ Invalid Git Action"


def init_workspace(branch_name: str) -> str:
    print(f"🚀 Initializing Workspace: {branch_name}")
    if QA_REPO_URL:
        res = git_action("clone")
        if "❌" in res: return res

    status = git_action("status")
    if status.strip().replace("Output:\n", ""): return "❌ ABORT: Uncommitted changes."

    git_action("checkout", branch="main")
    git_action("pull", branch="main")
    git_action("checkout", branch=branch_name, new=True)
    return f"✅ Workspace Ready on '{branch_name}'"


def file_op(action, file_path, content=None, directory="."):
    full_path = os.path.join(TARGET_REPO_PATH, file_path if file_path else directory)
    try:
        if action == "write":
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✅ Written: {file_path}"
        elif action == "read":
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif action == "list":
            files = []
            for root, _, filenames in os.walk(full_path):
                for filename in filenames:
                    rel = os.path.relpath(os.path.join(root, filename), TARGET_REPO_PATH)
                    if not rel.startswith((".git", ".venv", "results")): files.append(rel)
            return "\n".join(files[:30])
    except Exception as e:
        return f"Error: {e}"


# Tool Map
TOOL_MAP = {
    "read_jira_ticket": read_jira_ticket,
    "init_workspace": init_workspace,
    "git_checkout": lambda branch_name: git_action("checkout", branch=branch_name, new=True),
    "git_pull": lambda branch_name="main": git_action("pull", branch=branch_name),
    "git_commit": lambda message: git_action("commit", message=message),
    "git_push": lambda branch_name: git_action("push", branch=branch_name),
    "write_file": lambda file_path, content: file_op("write", file_path, content),
    "read_file": lambda file_path: file_op("read", file_path),
    "list_files": lambda directory=".": file_op("list", None, directory=directory),
    "run_shell_command": run_shell_command
}


# ==============================================================================
# 🚀 MAIN AGENT LOOP (Callable Function)
# ==============================================================================
def run_qa_agent_task(task_description: str):
    print(f"📡 Remote QA Agent connecting to: {TARGET_REPO_PATH}")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": task_description}]

    final_result = ""

    while True:
        try:
            response = requests.post(OLLAMA_API_URL, json={"model": MODEL_NAME, "messages": messages, "stream": False},
                                     timeout=120)
            ai_msg = response.json()["message"]["content"]

            try:
                json_str = ai_msg.strip()
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()
                tool_call = json.loads(json_str)
            except:
                print(f"🤖 AI: {ai_msg}")
                if "task_complete" in ai_msg.lower() or "mission accomplished" in ai_msg.lower():
                    final_result = ai_msg
                    break
                messages.append({"role": "assistant", "content": ai_msg})
                continue

            action = tool_call.get("action")
            args = tool_call.get("args", {})
            print(f"🤖 Action: {action} | Args: {args}")

            if action in TOOL_MAP:
                try:
                    result = TOOL_MAP[action](**args)
                except Exception as e:
                    result = f"❌ Error: {e}"
            else:
                result = f"❌ Unknown tool: {action}"

            print(f"⚙️ Result: {result[:100]}...")
            messages.append({"role": "assistant", "content": json.dumps(tool_call)})
            messages.append({"role": "user", "content": f"Result: {result}"})

            if "❌ ABORT" in result:
                final_result = "Aborted due to error."
                break

        except Exception as e:
            return f"❌ Critical Error: {e}"

    return final_result