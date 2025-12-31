# ไฟล์: debug_startup.py
import sys
import os

# 1. ตั้งค่า Path ให้เหมือนตอนรันจริง
sys.path.append(os.getcwd())

print("🔍 Testing Imports...")

try:
    # 2. ลอง Import ไฟล์ main เพื่อดูว่าพังตรงไหน
    # (ถ้ามี Syntax Error หรือ Import ผิด มันจะฟ้องทันทีตรงนี้)
    from mcp_server import main

    print("✅ Import main success!")

    # 3. ลอง Import Tools ใหม่ที่เพิ่งเพิ่ม
    print("🔍 Testing Git Ops...")
    from graph.tools import git_ops

    print("✅ Import git_ops success!")

    print("🔍 Testing File Ops...")
    from graph.tools import file_ops

    print("✅ Import file_ops success!")

except Exception as e:
    print("\n❌ FOUND THE ERROR! 👇")
    import traceback

    traceback.print_exc()  # ปริ้น Error ตัวเต็มออกมา