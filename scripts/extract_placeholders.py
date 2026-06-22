# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import subprocess

def get_slide_count(ppt_path):
    res = subprocess.run(["officecli", "view", ppt_path, "stats"], capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        match = re.search(r"Slides:\s*(\d+)", res.stdout)
        if match:
            return int(match.group(1))
    return 0

def extract_placeholders(ppt_path):
    slide_count = get_slide_count(ppt_path)
    if slide_count == 0:
        print(f"Error: Could not determine slide count or file is empty: {ppt_path}")
        return None

    print(f"Detected {slide_count} slides. Extracting placeholders...")
    results = {}
    for slide_idx in range(1, slide_count + 1):
        path = f"/slide[{slide_idx}]"
        res = subprocess.run(["officecli", "get", ppt_path, path, "--json"], capture_output=True, text=True, encoding="utf-8")
        if res.returncode == 0:
            try:
                slide_data = json.loads(res.stdout)
                shapes_info = []
                def walk_nodes(node):
                    if not isinstance(node, dict):
                        return
                    node_type = node.get("type")
                    node_text = node.get("text", "").strip()
                    
                    if node_type in ["textbox", "shape", "cell", "table-cell"] and node_text:
                        if len(node_text) > 1 and not re.match(r"^[0-9a-fA-F]{30,}$", node_text):
                            shapes_info.append({
                                "path": node.get("path"),
                                "text": node_text,
                                "id": node.get("format", {}).get("id"),
                                "type": node_type,
                                "name": node.get("format", {}).get("name")
                            })
                    if "children" in node:
                        for child in node["children"]:
                            walk_nodes(child)
                            
                if "data" in slide_data and "results" in slide_data["data"]:
                    for root_node in slide_data["data"]["results"]:
                        walk_nodes(root_node)
                if shapes_info:
                    results[f"slide_{slide_idx}"] = shapes_info
            except Exception as e:
                print(f"Error parsing slide {slide_idx}: {e}")
        else:
            print(f"Error reading slide {slide_idx}: {res.stderr}")
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_placeholders.py <path_to_pptx> [<output_json>]")
        sys.exit(1)
    
    ppt = sys.argv[1]
    # Enforce default to local Tmp directory if it exists
    default_out = "Tmp/placeholders.json" if os.path.exists("Tmp") else "placeholders.json"
    out = sys.argv[2] if len(sys.argv) > 2 else default_out
    
    data = extract_placeholders(ppt)
    if data:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Successfully extracted placeholders to {out}!")
