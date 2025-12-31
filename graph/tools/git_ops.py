import os
import subprocess
import shutil
from langchain_core.tools import tool

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_git_command(args: list):
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Git Error: {e.stderr}"


@tool
def git_create_branch(branch_name: str):
    """
    Create and switch to a new git branch.
    Example: 'feature/SCRUM-11-payment-api'
    """
    # 1. เช็คก่อนว่ามีอะไรค้างไหม
    status = run_git_command(["status", "--porcelain"])
    if status and "Git Error" not in status:
        return "Error: You have uncommitted changes. Please commit or stash them first."

    # 2. สร้างและสลับ branch
    return run_git_command(["checkout", "-b", branch_name])


@tool
def git_commit_changes(message: str):
    """
    Stage all changes and commit with a message.
    Example: 'feat: implement payment intent model'
    """
    # 1. Git Add All
    add_res = run_git_command(["add", "."])
    if "Git Error" in add_res:
        return add_res

    # 2. Git Commit
    return run_git_command(["commit", "-m", message])


@tool
def git_status():
    """Check current git status and branch."""
    return run_git_command(["status"])

# ไฟล์ graph/tools/git_ops.py

@tool
def git_push_to_remote(branch_name: str):
    """
    Push the current branch to remote (origin).
    IMPORTANT: This requires SSH key or cached credentials to be configured on the machine.
    """
    # Push ไปที่ origin ตามชื่อ branch ที่ระบุ
    return run_git_command(["push", "-u", "origin", branch_name])


@tool
def create_pull_request(title: str, body: str, branch: str):
    """
    Create a Pull Request on GitHub using 'gh' CLI.
    Must be called AFTER pushing the branch.
    """
    # ตรวจสอบว่ามี gh-cli ไหม
    if not shutil.which("gh"):
        return "Error: GitHub CLI (gh) is not installed on the server."

    try:
        # คำสั่งสร้าง PR: gh pr create --title "..." --body "..." --head ... --base main
        result = subprocess.run(
            [
                "gh", "pr", "create",
                "--title", title,
                "--body", body,
                "--head", branch,
                "--base", "main" # หรือ master แล้วแต่โปรเจกต์
            ],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        return f"✅ Pull Request Created Successfully: {result.stdout.strip()}"
    except subprocess.CalledProcessError as e:
        return f"Failed to create PR: {e.stderr}"
