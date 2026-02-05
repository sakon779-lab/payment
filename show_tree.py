import os

# 🚫 รายชื่อโฟลเดอร์ที่จะ "ไม่ย้าย" (Payment App Specific + System)
IGNORE = {
    # System Folders
    '.git', '.venv', '.idea', '__pycache__', 
    
    # Payment App Folders (ทิ้งไว้ที่เดิม)
    'payment_core', 
    'src', 
    'alembic', 
    'pg_data', 
    'tests',   # Test ของแอปฯ เดิม
    
    # Output Folders
    'results', 'node_modules', 'dist', 'build'
}

def print_tree(dir_path, prefix=''):
    try:
        items = os.listdir(dir_path)
    except PermissionError:
        return

    # แยกไฟล์กับโฟลเดอร์
    files = [i for i in items if os.path.isfile(os.path.join(dir_path, i)) and i not in IGNORE]
    dirs = [i for i in items if os.path.isdir(os.path.join(dir_path, i)) and i not in IGNORE]

    files.sort()
    dirs.sort()

    # แสดงไฟล์
    for f in files:
        print(f"{prefix}📄 {f}")

    # แสดงโฟลเดอร์
    for d in dirs:
        print(f"{prefix}📁 {d}/")
        print_tree(os.path.join(dir_path, d), prefix + "    ")

if __name__ == "__main__":
    print(f"🏛️  Preview: Candidates for 'Olympus-Agents' Repo")
    print(f"📂 Source: {os.getcwd()}")
    print("-" * 40)
    print_tree(".")
    print("-" * 40)