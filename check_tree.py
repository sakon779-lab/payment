import os


def print_tree(startpath):
    print(f"📂 Project Structure: {os.path.basename(os.path.abspath(startpath))}")
    for root, dirs, files in os.walk(startpath):
        # รายชื่อโฟลเดอร์ที่จะไม่แสดง (กรองออก)
        dirs[:] = [d for d in dirs if
                   d not in ['pg_data','.git', '__pycache__', '.venv', 'env', '.idea', '.vscode', 'node_modules']]

        level = root.replace(startpath, '').count(os.sep)
        indent = '│   ' * level
        print(f'{indent}├── {os.path.basename(root)}/')

        subindent = '│   ' * (level + 1)
        for f in files:
            if f.endswith('.pyc') or f == '.DS_Store': continue
            print(f'{subindent}├── {f}')


if __name__ == "__main__":
    print_tree('.')