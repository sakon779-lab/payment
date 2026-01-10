import json
import logging
import re
import subprocess
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

# ✅ เพิ่มบรรทัดนี้ครับ! ไม่งั้นฟังก์ชัน init_workspace จะพังเพราะหาตัวแปรไม่เจอ
PROJECT_ROOT = "D:\WorkSpace"
# หรือใส่ Path เต็ม เช่น: PROJECT_ROOT = r"D:\Project\PaymentBlockChain"

# ----------------------------------------------------
# 🆕 New Tool: Init Workspace Logic (Safety First)
# ----------------------------------------------------
def init_workspace(branch_name: str, base_branch: str = "main") -> str:
    """
    Safety Check & Setup:
    1. Force change directory to PROJECT_ROOT.
    2. Check for uncommitted changes (must be clean).
    3. Checkout base branch (main/master).
    4. Pull latest changes.
    5. Create and checkout new feature branch.
    """
    try:
        # 0. 🎯 Lock Workspace
        if PROJECT_ROOT and PROJECT_ROOT != ".":
            if os.path.exists(PROJECT_ROOT):
                os.chdir(PROJECT_ROOT)
                logger.info(f"📂 Changed working directory to: {os.getcwd()}")
            else:
                return f"❌ Error: Path '{PROJECT_ROOT}' does not exist."

        # 1. Check Dirty
        # ใช้ shell=True ใน Windows บางครั้งช่วยแก้ปัญหาหา git ไม่เจอ แต่ระวังเรื่อง security (ใน local ไม่เป็นไร)
        status = subprocess.check_output("git status --porcelain", shell=True, text=True).strip()
        if status:
            return f"❌ ABORT: Workspace is dirty (uncommitted changes). Please commit or stash them first.\n\n{status}"

        # 2. Checkout Base & Pull
        subprocess.run(f"git checkout {base_branch}", shell=True, check=True, capture_output=True)
        pull_result = subprocess.run(f"git pull origin {base_branch}", shell=True, capture_output=True, text=True)

        if pull_result.returncode != 0:
            logger.warning(f"⚠️ Git Pull Warning: {pull_result.stderr}")

        # 3. Create & Checkout New Branch (-B เพื่อ reset ถ้าชื่อซ้ำ)
        subprocess.run(f"git checkout -B {branch_name}", shell=True, check=True, capture_output=True)

        return f"✅ Workspace Initialized:\n- Location: {os.getcwd()}\n- Cleaned & Synced '{base_branch}'\n- Switched to new branch '{branch_name}'\n- Ready to code."

    except subprocess.CalledProcessError as e:
        return f"❌ Git Error: {e}"
    except Exception as e:
        return f"❌ Error initializing workspace: {e}"

# ----------------------------------------------------
# รวม Tools ทั้งหมดไว้ที่เดียว
# ----------------------------------------------------
# ✅ แก้ตรงนี้: ใส่ Type Hint : Dict[str, Any] เพื่อบอก IDE ว่า "อย่าเรื่องมาก รับได้หมด"
TOOLS: Dict[str, Any] = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "generate_skeleton": generate_skeleton,
    "init_workspace": init_workspace, # ✅ เพิ่มตรงนี้
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
Your goal is to implement features safely using Git version control.

*** SAFETY PROTOCOL ***
1. START EVERY TASK by using `init_workspace(branch_name="...")`.
   - Do NOT edit files on 'main' or 'master'.
   - Do NOT start coding until you successfully enter a new branch.
2. If `init_workspace` fails (e.g., dirty repo), STOP and report to the user.

TOOLS AVAILABLE:
1. init_workspace(branch_name, base_branch="main") -> Use this FIRST.
2. list_files(directory=".")
3. read_file(file_path)
4. write_file(file_path, content)
5. git_commit(message)
6. git_push(branch_name)
7. task_complete(summary)

RESPONSE FORMAT (JSON ONLY):

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
    แกะ JSON แบบอัจฉริยะ (ใช้ Decoder ของ Python เอง)
    รองรับ Nested JSON และ Multiple JSONs ต่อกันได้ 100%
    """
    results = []
    decoder = json.JSONDecoder()
    pos = 0

    while pos < len(text):
        # 1. ข้ามตัวอักษรขยะ จนกว่าจะเจอ '{'
        try:
            # หาตำแหน่งเริ่มต้นของปีกกาเปิด
            search = re.search(r"\{", text[pos:])
            if not search:
                break  # ไม่เหลือ JSON แล้ว

            start_index = pos + search.start()

            # 2. ให้ Python Decoder ช่วยแกะ JSON object ออกมา
            # raw_decode จะคืนค่า (object, index_ที่จบ)
            obj, end_index = decoder.raw_decode(text, idx=start_index)

            # 3. ตรวจสอบและเก็บผลลัพธ์
            if isinstance(obj, dict) and "action" in obj:
                results.append(obj)

            # 4. ขยับ Cursor ไปต่อท้าย JSON ที่เพิ่งแกะได้
            pos = end_index

        except json.JSONDecodeError:
            # ถ้าแกะพัง ให้ขยับไปข้างหน้า 1 ช่องแล้วลองใหม่
            pos += 1
        except Exception as e:
            logger.error(f"Error extracting JSON: {e}")
            break

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