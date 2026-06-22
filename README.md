# 🛠️ Populating Office Templates Custom Skill

这是一个专为 AI 编码助手（如 Google Antigravity、Codex 或 Claude Code）打造的自定义技能（Skill），用于实现 **PPT/Word 模板的精准页面重构与基于物理 ID 的文本/数据批量注入**。

该技能通过 OpenXML 稳定的唯一路径（如 `/slide[N]/shape[@id=XXXX]`）进行文本定位替换，完美保留模板原本的字体、色值与排版结构，避免字面值替换导致的格式损坏。

---

## 📋 依赖要求 (Dependencies)

在运行本技能脚本前，请确保您的系统中已安装以下依赖项：

1. **Python 3.x**
   - 脚本完全使用 Python 标准库实现，**无需安装任何第三方库**（如 `python-pptx` 或 `openpyxl` ），开箱即用。
2. **OfficeCLI**
   - **下载与项目地址**：[iOfficeAI/OfficeCLI](https://github.com/iOfficeAI/OfficeCLI.git)
   - **安装命令**：
     - **Windows (PowerShell)**:
       ```powershell
       irm https://d.officecli.ai/install.ps1 | iex
       ```
     - **macOS / Linux**:
       ```bash
       curl -fsSL https://d.officecli.ai/install.sh | bash
       ```
     安装后请确保命令行中能成功运行 `officecli --version`。

---

## 📂 结构说明 (Directory Structure)

```
populating-office-templates/
  ├── SKILL.md              # 技能的核心操作说明与逻辑约束流程
  ├── README.md             # 本说明文件
  ├── examples/
  │   └── ppt_bp_mapping_example.json  # 数据填充 JSON 样例
  └── scripts/
      ├── extract_placeholders.py      # 深度优先提取占位符路径和ID的脚本
      └── batch_injector.py            # 读取JSON配置并执行单事务批量注入的脚本
```

---

## 🚀 快速开始 (Quick Start)

### 第一步：提取模板中的占位符路径与 ID
使用 `extract_placeholders.py` 脚本，将模板 PPT 中的所有可编辑文本框及表格单元格提取成 JSON 结构：
```bash
python scripts/extract_placeholders.py "/path/to/template.pptx" "placeholders.json"
```

### 第二步：编辑内容映射
打开生成的 `placeholders.json`，在对应的唯一 ID 下填入您想替换的真实中文业务数据，保存文件（例如命名为 `mapping.json`）。格式如：
```json
[
  {
    "path": "/slide[1]/shape[@id=100002]",
    "text": "您的真实大标题内容"
  }
]
```

### 第三步：一键原子注入
运行 `batch_injector.py` 脚本，将内容一键安全地写入 PPT 副本中：
```bash
python scripts/batch_injector.py "/path/to/template.pptx" "mapping.json"
```

---

## ⚙️ 技能部署与激活 (How to Install as a Skill)

若要让您的 AI 编码助手在以后的对话中自动检索并加载该技能，您可以将整个 `populating-office-templates` 目录复制到以下路径之一：

* **全局生效（推荐）**：
  复制到 `C:\Users\<您的用户名>\.gemini\config\skills/populating-office-templates`
* **项目私有生效**：
  复制到当前项目根目录下的 `.agents/skills/populating-office-templates`
