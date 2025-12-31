# ไฟล์: graph/tools/git_ops.py
import os
import subprocess
import shutil
import logging
from langchain_core.tools import tool

# Setup Logger
logger = logging.getLogger(__name__)

# หา Path ของ Project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_git_command(args: list):
    """รันคำสั่ง Git แบบห้ามถาม (Non-interactive)"""
    command_str = " ".join(["git"] + args)
    logger.info(f"⏳ GIT RUNNING: {command_str}")

    try:
        # 👇 เทคนิคสำคัญ: ปิดการถาม Password/Prompt
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        result = subprocess.run(
            ["git"] + args,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=True,
            env=env  # 👈 ใส่ env เข้าไป
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip()
        logger.error(f"❌ GIT ERROR: {error_msg}")
        # ส่ง Error กลับไปให้ AI รู้เรื่อง (แทนที่จะเงียบ)
        return f"Git Error: {error_msg}"


@tool
def git_create_branch(branch_name: str):
    """Create and switch to a new git branch."""
    # 1. เช็ค Status ก่อน
    status = run_git_command(["status", "--porcelain"])
    if status and "Git Error" not in status:
        return "Error: You have uncommitted changes. Please commit or stash them first."

    # 2. สร้าง Branch
    return run_git_command(["checkout", "-b", branch_name])


@tool
def git_commit_changes(message: str):
    """Stage all changes and commit."""
    run_git_command(["add", "."])
    return run_git_command(["commit", "-m", message])


@tool
def git_status():
    """Check status."""
    return run_git_command(["status"])


@tool
def git_push_to_remote(branch_name: str):
    """Push to origin."""
    return run_git_command(["push", "-u", "origin", branch_name])


@tool
def create_pull_request(title: str, body: str, branch: str):
    """Create GitHub PR (Non-interactive)"""
    if not shutil.which("gh"):
        return "Error: GitHub CLI (gh) is not installed."

    try:
        # gh cli ปกติจะไม่ถามถ้า input ครบ
        cmd = [
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--head", branch,
            "--base", "main"
        ]

        result = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        return f"✅ PR Created: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"PR Failed: {e.stderr}"