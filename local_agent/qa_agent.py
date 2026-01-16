import os
import subprocess
import json
import requests
import sys
import base64


# ==============================================================================
# 🛠️ ENV LOADER (Dependency-Free)
# ==============================================================================
def load_env():
    """Loads environment variables from a .env file if it exists."""
    env_path = ".env"
    if not os.path.exists(env_path):
        print("⚠️ Warning: .env file not found. Skipping environment load.")
        return

    print(f"🌍 Loading environment variables from {env_path}...")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            # Skip comments and empty lines
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Split key=value
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')  # Remove quotes
                os.environ[key] = value


# Load immediately on import/start
load_env()

# ==============================================================================
# ⚙️ CONFIGURATION
# ==============================================================================
TARGET_REPO_PATH = r"D:\WorkSpace\QaAutomationAgent"
QA_REPO_URL = "https://github.com/sakon779-lab/qa-automation-repo.git"

# --- JIRA CONFIG (Loaded from .env) ---
# ใช้ os.getenv ดึงค่าจาก .env ถ้าไม่มีให้เป็น None
JIRA_BASE_URL = os.getenv("JIRA_URL")
JIRA_USER_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# --- AI CONFIG ---
OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5-coder:14b"

# ==============================================================================
# 🧠 SYSTEM PROMPT
# ==============================================================================
SYSTEM_PROMPT = f"""
You are "Gamma", a Senior QA Automation Engineer.
You operate on a separate repository located at: `{TARGET_REPO_PATH}`

Your goal is to manage the **QA Automation Repository** (Robot Framework).

*** WORKFLOW (STRICT ORDER) ***
1. **ANALYZE**: 
   - If User provides a Ticket ID (e.g., SCRUM-24), use `read_jira_ticket`.
   - Otherwise, interpret requirements from input.
2. **INIT**: `init_workspace(branch_name)`
   - Checks out the branch (Clones/Pulls automatically).
3. **PLAN & CODE**: 
   - Plan Data Isolation (`${{uuid}}`) and Mocking.
   - `write_file` to create tests (`tests/payment_service/...`).
4. **VERIFY**: `run_shell_command("robot ...")`
   - ALWAYS run tests locally.
5. **DELIVERY**: 
   - `git_commit(...)`
   - `git_push(...)`

*** CODING RULES (ROBOT FRAMEWORK) ***
- **Isolation**: Use `${{uuid}}` for unique data.
- **Mocking**: Setup/Teardown MockServer (Port 1080).

TOOLS AVAILABLE:
1. read_jira_ticket(issue_key)
2. init_workspace(branch_name)
3. git_checkout(branch_name)
4. git_pull(branch_name)
5. write_file(file_path, content)
6. read_file(file_path)
7. run_shell_command(command)
8. list_files(directory)
9. git_commit(message)
10. git_push(branch_name)

RESPONSE FORMAT (JSON ONLY):
{{ "action": "tool_name", "args": {{ ... }} }}
"""


# ==============================================================================
# 🛠️ JIRA INTEGRATION TOOL (Real API)
# ==============================================================================
def read_jira_ticket(issue_key: str) -> str:
    """Fetches issue details from Jira Cloud REST API."""
    print(f"🔍 Fetching Jira Ticket: {issue_key}...")

    if not JIRA_USER_EMAIL or not JIRA_API_TOKEN or not JIRA_BASE_URL:
        return (f"⚠️ Jira Config Missing in .env! "
                f"Please provide JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN.")

    # Jira API Auth
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"
    auth_str = f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}"
    auth_base64 = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            fields = data.get('fields', {})
            summary = fields.get('summary', 'No Summary')
            description = fields.get('description', {})
            return f"TICKET: {issue_key}\nSUMMARY: {summary}\nDESCRIPTION (JSON): {json.dumps(description)}"
        elif response.status_code == 404:
            return f"❌ Ticket {issue_key} not found."
        else:
            return f"❌ Jira API Error: {response.status_code} - {response.text}"

    except Exception as e:
        return f"❌ Connection Error: {e}"


# ==============================================================================
# 🛠️ CORE TOOLS
# ==============================================================================
def run_shell_command(command: str, cwd: str = None) -> str:
    work_dir = cwd if cwd else TARGET_REPO_PATH
    if command.startswith("robot") and work_dir == TARGET_REPO_PATH:
        os.makedirs(os.path.join(work_dir, "results"), exist_ok=True)
        if "--outputdir" not in command:
            command = f"{command} --outputdir results"

    print(f"💻 Executing in '{work_dir}': {command}")
    try:
        result = subprocess.run(
            command, shell=True, cwd=work_dir,
            capture_output=True, text=True, encoding='utf-8'
        )
        output = result.stdout + "\n" + result.stderr
        return f"Output:\n{output}" if result.returncode == 0 else f"❌ Failed:\n{output}"
    except Exception as e:
        return f"❌ Error: {e}"


def git_clone(repo_url: str) -> str:
    if os.path.exists(os.path.join(TARGET_REPO_PATH, ".git")):
        return "✅ Repo already exists."
    print(f"📥 Cloning from {repo_url}...")
    os.makedirs(TARGET_REPO_PATH, exist_ok=True)
    return run_shell_command(f"git clone {repo_url} .", cwd=TARGET_REPO_PATH)


def git_status() -> str:
    return run_shell_command("git status --porcelain", cwd=TARGET_REPO_PATH)


def git_pull(branch_name: str = "main") -> str:
    print(f"⬇️ Pulling {branch_name}...")
    return run_shell_command(f"git pull origin {branch_name}", cwd=TARGET_REPO_PATH)


def git_checkout(branch_name: str, create_new: bool = True) -> str:
    print(f"🌿 Checking out {branch_name}...")
    res = run_shell_command(f"git checkout {branch_name}", cwd=TARGET_REPO_PATH)
    if ("error" in res.lower() or "did not match" in res.lower()) and create_new:
        print(f"✨ Creating new branch {branch_name}...")
        return run_shell_command(f"git checkout -b {branch_name}", cwd=TARGET_REPO_PATH)
    return res


def git_commit(message: str) -> str:
    run_shell_command("git add .", cwd=TARGET_REPO_PATH)
    return run_shell_command(f'git commit -m "{message}"', cwd=TARGET_REPO_PATH)


def git_push(branch_name: str) -> str:
    return run_shell_command(f"git push origin {branch_name}", cwd=TARGET_REPO_PATH)


def init_workspace(branch_name: str) -> str:
    print(f"🚀 Initializing Workspace for: {branch_name}")
    if QA_REPO_URL:
        res = git_clone(QA_REPO_URL)
        if "❌" in res: return res
    elif not os.path.exists(TARGET_REPO_PATH):
        return f"❌ Error: Target path {TARGET_REPO_PATH} missing and no URL provided."

    status = git_status()
    if status.strip().replace("Output:\n", ""):
        return "❌ ABORT: Uncommitted changes found. Commit or stash them first."

    git_checkout("main", create_new=False)
    git_pull("main")
    git_checkout(branch_name, create_new=True)
    return f"✅ Workspace Ready on '{branch_name}'"


def write_file(file_path: str, content: str) -> str:
    try:
        full_path = os.path.join(TARGET_REPO_PATH, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✅ File written: {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


def read_file(file_path: str) -> str:
    try:
        full_path = os.path.join(TARGET_REPO_PATH, file_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(directory: str = ".") -> str:
    try:
        full_path = os.path.join(TARGET_REPO_PATH, directory)
        files = []
        for root, _, filenames in os.walk(full_path):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), TARGET_REPO_PATH)
                if not rel_path.startswith((".git", ".venv", "results")):
                    files.append(rel_path)
        return "\n".join(files[:30])
    except Exception as e:
        return f"Error listing files: {e}"


# ==============================================================================
# 🧩 TOOL MAPPING
# ==============================================================================
TOOL_MAP = {
    "read_jira_ticket": read_jira_ticket,
    "init_workspace": init_workspace,
    "git_checkout": lambda branch_name: git_checkout(branch_name, create_new=True),
    "git_pull": git_pull,
    "write_file": write_file,
    "read_file": read_file,
    "list_files": list_files,
    "run_shell_command": run_shell_command,
    "git_commit": git_commit,
    "git_push": git_push
}

# ==============================================================================
# 🤖 AI ENGINE
# ==============================================================================
messages = [{"role": "system", "content": SYSTEM_PROMPT}]


def run_qa_agent(user_input: str):
    print(f"📡 Remote QA Agent connecting to: {TARGET_REPO_PATH}")
    print(f"📋 Mission: {user_input}")
    print("=" * 60)
    messages.append({"role": "user", "content": user_input})

    while True:
        try:
            response = requests.post(
                OLLAMA_API_URL,
                json={"model": MODEL_NAME, "messages": messages, "stream": False},
                timeout=120
            )
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
                if "task_complete" in ai_msg.lower() or "mission accomplished" in ai_msg.lower(): break
                messages.append({"role": "assistant", "content": ai_msg})
                continue

            action = tool_call.get("action")
            args = tool_call.get("args", {})
            print(f"🤖 Action: {action} | Args: {args}")

            if action in TOOL_MAP:
                try:
                    result = TOOL_MAP[action](**args)
                except TypeError as e:
                    result = f"❌ Argument Mismatch: {e}"
                except Exception as e:
                    result = f"❌ Execution Error: {e}"
            else:
                result = f"❌ Unknown tool: {action}"

            print(f"⚙️ Result: {result[:200]}...")
            messages.append({"role": "assistant", "content": json.dumps(tool_call)})
            messages.append({"role": "user", "content": f"Result: {result}"})

            if "❌ ABORT" in result: break

        except Exception as e:
            print(f"❌ Critical Error: {e}")
            break


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "Check Status"
    run_qa_agent(task)