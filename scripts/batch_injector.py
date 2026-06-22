# -*- coding: utf-8 -*-
import sys
import json
import subprocess
import tempfile
import os

def inject_text(ppt_path, mapping_json):
    if not os.path.exists(mapping_json):
        print(f"Error: Mapping JSON file not found: {mapping_json}")
        return False

    with open(mapping_json, "r", encoding="utf-8") as f:
        try:
            mapping_data = json.load(f)
        except Exception as e:
            print(f"Error reading mapping JSON: {e}")
            return False

    commands = []
    # Support both list of replacements and dict of slide shapes
    if isinstance(mapping_data, list):
        for item in mapping_data:
            if "path" in item and "text" in item:
                commands.append({
                    "command": "set",
                    "path": item["path"],
                    "props": {"text": item["text"]}
                })
    elif isinstance(mapping_data, dict):
        for slide_key, shapes in mapping_data.items():
            for shape in shapes:
                if "path" in shape and "text" in shape:
                    commands.append({
                        "command": "set",
                        "path": shape["path"],
                        "props": {"text": shape["text"]}
                    })
    
    if not commands:
        print("No valid commands to execute.")
        return False

    print(f"Prepared {len(commands)} text replacement commands.")
    
    # Enforce temporary file creation within the local Tmp/ folder if it exists
    temp_dir = "Tmp" if os.path.exists("Tmp") else None
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", dir=temp_dir, delete=False, encoding="utf-8") as tmp:
        json.dump(commands, tmp, ensure_ascii=False, indent=2)
        tmp_name = tmp.name

    try:
        print("Running officecli batch injection...")
        res = subprocess.run(["officecli", "batch", ppt_path, "--input", tmp_name, "--stop-on-error"], capture_output=True, text=True, encoding="utf-8")
        if res.returncode == 0:
            print("Injection completed successfully!")
            print(res.stdout)
            return True
        else:
            print("Error running batch injection:")
            print(res.stderr)
            return False
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python batch_injector.py <path_to_pptx> <path_to_mapping_json>")
        sys.exit(1)
    
    ppt = sys.argv[1]
    mapping = sys.argv[2]
    
    inject_text(ppt, mapping)
