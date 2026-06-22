# 🛠️ Populating Office Templates - AI Custom Skill

这是一个专为 AI 编码助手（如 Google Antigravity、Codex 或 Claude Code）设计的自定义技能（Skill）。

通过该技能，您只需向 AI 发送一条指令并提供**模板**与**文档**，AI 就会在后台自动重构幻灯片页面并基于物理 ID 精准注入文本，完美保障模板原本的字体、色值与排版，无需任何繁琐的人工命令操作。

---

## 🚀 极简使用流程 (Quick Start)

### 1. 安装 (Install)
将此仓库克隆到您 AI 助手的自定义技能目录中：

```bash
# 进入您的 AI 助手技能目录（例如 ~/.gemini/config/skills/ 或项目本地 .agents/skills/）
git clone https://github.com/ZhangJing-gugugaga/PPT-templates-skill.git populating-office-templates
```

### 2. 使用 (Usage)
您不需要手动运行任何脚本。在对话框中，直接使用**斜杠（或口头提及）触发该技能**并提供您的模板与商业计划书文档：

> 💬 **指令示例：**
> "使用 `/populating-office-templates` 技能，基于 `Templates/0008_template.pptx` 模板和 `生息守护_商业计划书.md` 商业计划书，生成一份路演 PPT，输出到 `Result/` 目录下。"

### 3. 后台自动化工作流 (Under the Hood)
当您输入上述指令后，AI 助手会根据技能自动执行以下动作：
1. **重构**：自动生成结构调整命令，在 `Result/` 中生成具有指定物理页数的 PPT 框架。
2. **审计**：自动在后台运行 `scripts/extract_placeholders.py` 提取模板页的底层物理 ID 映射。
3. **映射**：根据您的商业计划书内容，自动在后台生成 `Tmp/mapping.json` 对齐物理 ID 与文本。
4. **注入**：自动在后台调用 `scripts/batch_injector.py`，以单事务形式原子注入文字，并清理临时文件。

---

## 🖼️ 效果示例 (Visual Examples)

使用本技能处理前后的幻灯片页面对比：

| 修改前（模板原始状态） | 修改后（使用本技能注入中文业务数据后） |
| :---: | :---: |
| ![修改前](images/模板示例.png) | ![修改后](images/skills后的PPT.png) |

---

## 📂 目录结构 (Directory Structure)

```
populating-office-templates/
  ├── SKILL.md              # 技能的核心操作规范（AI 自动阅读）
  ├── README.md             # 本说明文档（人类阅读）
  ├── Templates/            # 存放您的原始 PPT 模板（如 0008, 0010 模板）
  ├── Result/               # 存放最终生成的 PPT 结果文件
  ├── Tmp/                  # 运行期间自动存储临时映射文件的缓存区
  ├── images/               # 存放展示图片
  ├── examples/
  │   └── ppt_bp_mapping_example.json  # 数据填充 JSON 样例
  └── scripts/
      ├── extract_placeholders.py      # 自动提取占位符路径和ID的脚本
      └── batch_injector.py            # 执行单事务批量注入的脚本
```

---

## 📋 依赖要求 (Dependencies)

AI 助手运行此技能依赖以下本地环境：

1. **Python 3.x**（仅使用内置标准库，无需额外 `pip` 安装第三方依赖）。
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
