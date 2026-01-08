import json
import logging
import re
from typing import Dict, Any, Optional, List

# Import เครื่องมือที่เราเตรียมไว้
from local_agent.llm_client import query_qwen
from local_agent.tools.file_ops import list_files, read_file, write_file
from local_agent.tools.code_analysis import generate_skeleton

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DevAgent")

# --- System Prompt: กฎเหล็กสำหรับ Qwen ---
SYSTEM_PROMPT = """
You are a Senior Python Developer Agent working in a local environment.
Your goal is to implement features or fix bugs based on user requests.

**CRITICAL RULES:**
1. **Explore First:** Do NOT write code immediately. Check existing files using `list_files` and `generate_skeleton`.
2. **Token Efficiency:** Do NOT read full file content unless necessary. Use `generate_skeleton` to see class/function signatures.
3. **Implementation:** When writing code, output the FULL content of the file.
4. **Tool Usage:** You have access to tools. To use a tool, you must output a JSON block strictly in this format:

```json
{
  "action": "tool_name",
  "args": {
    "arg_name": "value"
  }
}```
AVAILABLE TOOLS:

list_files(directory="."): List all files.

generate_skeleton(file_path): Get signatures (Read-friendly).

read_file(file_path): Read full content (Use sparingly).

write_file(file_path, content): Write/Overwrite a file.

task_complete(summary): Call this when done. """


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    ฟังก์ชันช่วยแกะ JSON จากคำตอบของ AI
    รองรับทั้งแบบมี ```json ... ``` และแบบ JSON ล้วนๆ
    """
    try:
        # 1. พยายามหา block code json (```json ... ```)
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # 2. ถ้าไม่มี block code ลองหา { ... } แบบดิบๆ
        json_match_raw = re.search(r"(\{.*\})", text, re.DOTALL)
        if json_match_raw:
            return json.loads(json_match_raw.group(1))

    except json.JSONDecodeError:
        pass
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")

    return None


def run_dev_agent_task(task_description: str, max_steps: int = 15) -> str:
    """
    Main Loop ของ Dev Agent
    Args:
        task_description: คำสั่งงาน (เช่น "สร้าง API Login")
        max_steps: จำนวนรอบสูงสุดที่ให้ AI คิด
    """
    logger.info(f"🚀 Starting Task: {task_description}")

    # เริ่มต้น Chat History ด้วย System Prompt
    history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task_description}"}
    ]

    for step in range(max_steps):
        logger.info(f"🔄 Step {step + 1}/{max_steps}...")

        # 1. ส่ง Chat History ให้ Qwen คิด
        response = query_qwen(history)

        # Log คำตอบ AI (ตัดสั้นๆ เพื่อความสะอาดของ Log)
        log_resp = response[:100] + "..." if len(response) > 100 else response
        logger.info(f"🤖 AI Response: {log_resp}")

        # 2. แกะ JSON Tool Call จากคำตอบ
        tool_call = _extract_json(response)

        if not tool_call:
            # ถ้า AI ไม่เรียก Tool (พูดคุยเฉยๆ) ให้เก็บลง History แล้วไปต่อ
            history.append({"role": "assistant", "content": response})
            continue

        # 3. เตรียมรัน Tool
        action = tool_call.get("action")
        args = tool_call.get("args", {})
        result = ""

        logger.info(f"🔧 Executing Tool: {action}")

        try:
            # 4. เรียกใช้ฟังก์ชันจริงตามชื่อ Tool
            if action == "list_files":
                result = list_files(args.get("directory", "."))

            elif action == "generate_skeleton":
                result = generate_skeleton(args.get("file_path"))

            elif action == "read_file":
                result = read_file(args.get("file_path"))

            elif action == "write_file":
                # ตรวจสอบว่า parameter ครบไหม
                if "file_path" in args and "content" in args:
                    result = write_file(args.get("file_path"), args.get("content"))
                else:
                    result = "Error: Missing 'file_path' or 'content' in arguments."

            elif action == "task_complete":
                summary = args.get("summary", "Task finished.")
                logger.info(f"✅ Task Completed: {summary}")
                return f"SUCCESS: {summary}"

            else:
                result = f"Error: Unknown tool '{action}'"

        except Exception as e:
            result = f"Error executing tool: {str(e)}"

        # 5. ส่งผลลัพธ์ Tool กลับไปให้ AI รู้
        # (ต้องเก็บคำตอบ AI ก่อนหน้านี้ลง history ด้วย เพื่อให้บทสนทนาต่อเนื่อง)
        history.append({"role": "assistant", "content": response})
        history.append({"role": "user", "content": f"Tool Output ({action}):\n{result}"})

    return "❌ FAILED: Max steps reached."
