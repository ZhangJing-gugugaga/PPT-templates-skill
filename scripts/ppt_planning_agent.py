# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import argparse
import zipfile
import xml.etree.ElementTree as ET
import urllib.request
import subprocess

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def extract_theme_specs(pptx_path):
    """
    Extract color scheme and font scheme directly from theme1.xml inside pptx zip file.
    """
    namespaces = {
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
    }
    specs = {
        "colors": {},
        "fonts": []
    }
    
    if not os.path.exists(pptx_path):
        return specs
        
    try:
        with zipfile.ZipFile(pptx_path, 'r') as z:
            theme_xml_path = 'ppt/theme/theme1.xml'
            if theme_xml_path in z.namelist():
                theme_xml = z.read(theme_xml_path)
                # Decode to string safely to avoid regex encoding issues
                theme_xml_str = theme_xml.decode('utf-8', errors='ignore')
                root = ET.fromstring(theme_xml)
                
                # Extract colors from clrScheme
                clr_scheme = root.find('.//a:clrScheme', namespaces)
                if clr_scheme is not None:
                    for child in clr_scheme:
                        color_name = child.tag.split('}')[-1]
                        srgb = child.find('.//a:srgbClr', namespaces)
                        sys_clr = child.find('.//a:sysClr', namespaces)
                        if srgb is not None:
                            specs["colors"][color_name] = "#" + srgb.attrib.get('val', '')
                        elif sys_clr is not None:
                            specs["colors"][color_name] = "#" + sys_clr.attrib.get('lastClr', 'FFFFFF')
                
                # Extract font list using regex to capture all typefaces, including major, minor, ea and latin
                typefaces = re.findall(r'typeface="([^"]+)"', theme_xml_str)
                # Clean up and deduplicate, ignore placeholder fonts or empty ones
                unique_fonts = []
                for tf in typefaces:
                    tf_clean = tf.strip()
                    if tf_clean and tf_clean not in unique_fonts and not tf_clean.startswith('+'):
                        unique_fonts.append(tf_clean)
                specs["fonts"] = unique_fonts
    except Exception as e:
        print(f"[Warning] Failed to extract visual theme specs from pptx: {e}", file=sys.stderr)
        
    return specs

def run_placeholder_extraction(pptx_path, script_dir):
    """
    Run extract_placeholders.py and load its output placeholders.json.
    """
    placeholder_script = os.path.join(script_dir, "extract_placeholders.py")
    tmp_dir = os.path.join(os.path.dirname(script_dir), "Tmp")
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
        
    out_json = os.path.join(tmp_dir, "placeholders.json")
    
    # Run the script
    try:
        subprocess.run([sys.executable, placeholder_script, pptx_path, out_json], capture_output=True, check=True)
    except Exception as e:
        print(f"[Warning] extract_placeholders.py execution failed: {e}. Will try default extraction.", file=sys.stderr)
        
    # Read output
    if os.path.exists(out_json):
        try:
            with open(out_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to read placeholders JSON: {e}", file=sys.stderr)
    return {}

def extract_placeholders_pure_python(pptx_path):
    """
    Extract text runs from slides directly using zipfile and regex to bypass file lock conflicts.
    """
    results = {}
    if not os.path.exists(pptx_path):
        return results
    try:
        with zipfile.ZipFile(pptx_path, 'r') as z:
            slide_files = [f for f in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml', f)]
            # Natural sorting of slide files
            slide_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
            for idx, sf in enumerate(slide_files, 1):
                slide_xml = z.read(sf)
                slide_xml_str = slide_xml.decode('utf-8', errors='ignore')
                # Find all values inside <a:t>...</a:t>
                text_runs = re.findall(r'<a:t[^>]*>([^<]+)</a:t>', slide_xml_str)
                shapes_info = []
                for text in text_runs:
                    txt = text.strip()
                    # Skip single character noise or extremely long base64 strings
                    if len(txt) > 1 and not re.match(r"^[0-9a-fA-F]{30,}$", txt):
                        shapes_info.append({"text": txt})
                if shapes_info:
                    results[f"slide_{idx}"] = shapes_info
    except Exception as e:
        print(f"[Warning] Failed pure python placeholder extraction: {e}", file=sys.stderr)
    return results

def build_placeholders_summary(placeholders_data):
    """
    Formulate a brief summary of placeholders per slide for LLM layout matching.
    """
    summary = []
    # Sort slides by slide index
    slide_keys = sorted(placeholders_data.keys(), key=lambda x: int(x.split('_')[-1]) if '_' in x else 999)
    for key in slide_keys:
        shapes = placeholders_data[key]
        slide_num = key.split('_')[-1]
        texts = [s.get('text', '') for s in shapes if s.get('text')]
        # Truncate long texts
        texts_short = [t[:30] + "..." if len(t) > 30 else t for t in texts]
        # Keep only up to 4 texts to prevent token explosion
        summary_text = " / ".join(texts_short[:4])
        summary.append(f"- Slide {slide_num}: {summary_text}")
    return "\n".join(summary)

def call_openai_compatible_api(prompt, api_key, api_base, model):
    """
    Call OpenAI compatible Chat Completion API using pure python urllib.
    """
    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Ensure system context instructions are strong
    data = {
        "model": model,
        "messages": [
            {
                "role": "system", 
                "content": "You are a professional PPT developer agent. You follow rules strictly, perform precise layout planning, and output clean, structured Markdown documents."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.1
    }
    
    req_body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    
    try:
        print(f"Connecting to LLM API: {url} using model '{model}'...")
        with urllib.request.urlopen(req, timeout=90) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            return res_json['choices'][0]['message']['content']
    except Exception as e:
        print(f"\n[Error] LLM API Request failed: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="PPT Planning & Outline Development Agent")
    parser.add_argument("--template", required=True, help="Path to target PPTX template file")
    parser.add_argument("--source", required=True, help="Path to business plan source document (.md)")
    parser.add_argument("--ref", required=True, help="Path to PPT structure/outline reference (.txt)")
    parser.add_argument("--output", default="Result/ppt_development_document.md", help="Output path for the planning document")
    parser.add_argument("--api-key", help="LLM API Key (defaults to LLM_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY environment variables)")
    parser.add_argument("--api-base", default="https://api.openai.com/v1", help="LLM API Base URL")
    parser.add_argument("--model", default="gpt-4o", help="LLM Model Name")
    
    args = parser.parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    # Get API key from multiple environment fallbacks
    api_key = args.api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    api_base = os.environ.get("LLM_API_BASE") or args.api_base
    model = os.environ.get("LLM_MODEL") or args.model
    
    print("====== [PPT Planning Agent Phase 0] ======")
    
    # 1. Extract physical visual theme specs
    print(f"1. Extracting visual specifications from: {args.template}...")
    theme_specs = extract_theme_specs(args.template)
    
    colors_str = "\n".join([f"  - {k}: {v}" for k, v in theme_specs["colors"].items()])
    fonts_str = ", ".join(theme_specs["fonts"])
    print(f"   -> Colors extracted: {list(theme_specs['colors'].keys())}")
    print(f"   -> Fonts extracted: {fonts_str}")
    
    # 2. Extract slide placeholders text
    print("2. Extracting placeholders text...")
    placeholders_data = run_placeholder_extraction(args.template, script_dir)
    if not placeholders_data:
        print("   -> officecli extraction yielded no data (file may be locked). Trying pure Python extraction...")
        placeholders_data = extract_placeholders_pure_python(args.template)
        
    placeholders_summary = build_placeholders_summary(placeholders_data)
    slide_count = theme_specs["colors"].get("slide_count", len(placeholders_data))
    if slide_count == 0:
        slide_count = len(placeholders_data)
    print(f"   -> Found {slide_count} slides inside template.")
    
    # 3. Read input documents
    print(f"3. Reading source document: {args.source}...")
    try:
        with open(args.source, "r", encoding="utf-8") as f:
            source_content = f.read()
    except Exception as e:
        print(f"[Error] Failed to read source file: {e}", file=sys.stderr)
        sys.exit(1)
        
    print(f"4. Reading layout reference: {args.ref}...")
    try:
        with open(args.ref, "r", encoding="utf-8") as f:
            ref_content = f.read()
    except Exception as e:
        print(f"[Error] Failed to read reference file: {e}", file=sys.stderr)
        sys.exit(1)
        
    # 4. Construct final structured prompt
    print("5. Assembling final prompt with physical specs...")
    
    final_prompt = f"""你是一个专业的 PPT 设计开发规划 Agent。你的任务是根据下面提供的“PPT 模板真实视觉规范”和“物理占位符文本内容”，精读“商业计划书”与“结构参考要求”，为项目规划出高契合度的 PPT 逐页开发设计文档。

## 输入信息

### 1. 模板真实视觉规范（物理提取结果）
**配色色值**：
{colors_str}
**默认主题字体**：
  - {fonts_str}

### 2. 占位符文本参考（模板共 {slide_count} 页，包含每页特征文本，用于推断其原始排版结构与功能）
{placeholders_summary}

### 3. 商业计划书原文内容（核心数据源）
```markdown
{source_content}
```

### 4. PPT 结构参考与大纲要求
```text
{ref_content}
```

---

## 任务执行步骤（严格按顺序）

### 第一步：分析模板的真实视觉规范
请从上述“模板真实视觉规范”和“占位符文本参考”中，整理并填充本模板的实际配色、字体、版式清单。
⚠️ **所有视觉参数必须严格来自输入信息，不得自行臆造不存在的色值或字体。**

### 第二步：内容提取与分析
1. 精读商业计划书原文，提取各章节的核心数据指标、主要结论和商业亮点（投资人视角，强调商业价值）。
2. 根据 PPT 结构参考，划分并确认各部分的页数分配。

### 第三步：逐页规划
根据模板实际版式和物理页码，设计并规划 PPT 每一页的详细内容（总页数严格控制在 19-21 页范围内）。
每一页必须包含：
- **页码与章节**
- **页面类型**（如封面页、目录页、过渡页、内容页、数据比例页、团队介绍页、封底页等）
- **标题**（亮眼的、投资人视角的标题）
- **核心内容要点**：精炼为 3-5 个要点，拒绝大段文字堆砌。每个要点严格控制在 25 个汉字以内！
- **数据/图表需求**：写出该页需要展示的来自商业计划书原文的具体物理数据。
- **模板版式匹配**：绑定模板中的具体页码（如 Slide X）。
- **操作说明**：详细说明此页的具体操作（如“替换 Slide X 的占位符文本”、“复制 Slide Y 重新排列”等）。

### 第四步：输出开发文档
请以 Markdown 格式生成完整的开发文档。

---

## 约束条件与禁止行为

### 视觉规范约束
- [ ] **配色100%来自模板**：只能使用上述提取出的真实配色（如 {list(theme_specs['colors'].values())[:4]}），严禁使用其他任何自定义的 hex 色值（如 #1A1A2E 等）。
- [ ] **字体100%来自模板**：只能使用上述提取出的真实中英文字体（如 阿里巴巴普惠体 / {theme_specs['fonts'][0] if theme_specs['fonts'] else 'Alibaba PuHuiTi'}），严禁自定义。
- [ ] **版式100%来自模板**：所有页面版式必须直接绑定模板已有的具体 Slide 页码，不得设计任何模板中不存在的新版式。
- [ ] **禁止模糊表述**：严禁使用“与模板风格一致”、“参考模板设计”等模糊用语。色值、字体名、绑定的模板 Slide 页码必须物理写出！

### 内容与结构约束
- [ ] **不插入SVG**：所有图形元素保留模板原有的形状，不得写入插入 SVG 图形的指令。
- [ ] **基于模板改造**：保留原有的圆角卡片、平铺矩阵、双栏对比等排版，只替换文字和数据。
- [ ] **数据驱动**：数据必须 100% 对应商业计划书中的真实数值，严禁瞎编。
- [ ] **页数控制**：页数控制在 19-21 页之间。
- [ ] **极简控制**：每页要点不超过 5 条，且每个要点字数绝对控制在 25 字以内！

### 禁止行为
- ❌ 禁止自行设定非模板颜色。
- ❌ 禁止自行设定非模板字体。
- ❌ 禁止插入外部 SVG。
- ❌ 禁止凭空设计不存在的版式。
- ❌ 禁止文字堆砌或大段摘抄。

---

## 输出格式

请严格按以下格式输出完整的 Markdown 开发文档：

### 1. 模板视觉规范提取（从0008.pptx实际提取）

**配色方案**：
| 用途 | 色值 | 出现位置 |
|------|------|---------|
| 主色 | [从模板提取] | [哪些页面使用] |
| 辅色 | [从模板提取] | [哪些页面使用] |
| 强调色 | [从模板提取] | [哪些页面使用] |
| 背景色 | [从模板提取] | [哪些页面使用] |
| 文字色 | [从模板提取] | [哪些页面使用] |

**字体方案**：
| 层级 | 字体名称 | 字号 | 字重 | 出现位置 |
|------|---------|------|------|---------|
| 页面主标题 | [从模板提取] | [从模板提取] | [从模板提取] | [哪些页面] |
| 二级标题 | [从模板提取] | [从模板提取] | [从模板提取] | [哪些页面] |
| 正文要点 | [从模板提取] | [从模板提取] | [从模板提取] | [哪些页面] |
| 辅助注释 | [从模板提取] | [从模板提取] | [从模板提取] | [哪些页面] |

**版式清单**：
| 模板页码 | 版式类型 | 布局结构 | 可复用场景 |
|---------|---------|---------|-----------|
| Slide 1 | [类型] | [布局] | [适用内容] |
| Slide 2 | [类型] | [布局] | [适用内容] |
| ... | ... | ... | ... |

### 2. 逐页规划表

| 页码 | 章节 | 页面类型 | 标题 | 核心内容要点 | 数据/图表 | 模板版式 | 操作说明 |
|------|------|---------|------|-------------|----------|---------|---------|
| 1 | 封面 | 封面页 | [项目名称+一句话描述] | 参赛信息 | 无 | Slide X | 替换文本 |
| 2 | 市场 | 内容页 | [标题] | [3-5个要点] | [具体数据] | Slide X | 替换文本 |
| ... | ... | ... | ... | ... | ... | ... | ... |

### 3. 操作清单
- **保留并替换文本的页面**：[页码列表]
- **删除的页面**：[页码列表及删除原因]
- **需要合并的页面**：[原页码 → 合并后页码]
- **需要新增/复制的页面**：[基于哪个版式改造]

## 验证标准
- [ ] 模板视觉规范提取章节完整，所有色值、字体、版式均可追溯到0008.pptx
- [ ] 总页数在19-21页范围内
- [ ] 每一页都有明确的内容规划，无遗漏
- [ ] 所有数据均可追溯到商业计划书原文
- [ ] 所有页面版式均可追溯到模板中的具体页码
- [ ] 无任何自定义色值或字体，100%使用模板原有视觉规范
- [ ] 语言风格面向投资人，突出商业价值
- [ ] 每页核心要点不超过5条，无大段文字
- [ ] 不包含任何SVG插入操作
"""

    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 5. Execute API Call or output fallback prompt
    if api_key:
        print("6. API Key detected. Invoking Chat Completion API...")
        llm_response = call_openai_compatible_api(final_prompt, api_key, api_base, model)
        if llm_response:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(llm_response)
                print(f"\\n[Success] Development planning document generated successfully at: {{args.output}}!")
                sys.exit(0)
            except Exception as e:
                print(f"[Error] Failed to write output file: {{e}}", file=sys.stderr)
        else:
            print("[Warning] API call returned empty response or failed. Falling back to Prompt manual output.", file=sys.stderr)
            
    # Fallback mode
    fallback_prompt_path = os.path.join(output_dir if output_dir else ".", "prompt_for_llm.md")
    try:
        with open(fallback_prompt_path, "w", encoding="utf-8") as f:
            f.write(final_prompt)
        print(f"\\n====== [API FALLBACK] ======")
        print(f"No API key configured or API call failed. A fully assembled prompt has been written to:")
        print(f"  -> {{fallback_prompt_path}}")
        print(f"Please copy the prompt from that file, run it in any Chat LLM (e.g. Gemini, GPT-4),")
        print(f"and write the response back to: {{args.output}}")
        print(f"============================\\n")
    except Exception as e:
        print(f"[Error] Failed to write fallback prompt: {{e}}", file=sys.stderr)

if __name__ == "__main__":
    main()
