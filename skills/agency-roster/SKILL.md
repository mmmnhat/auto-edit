---
name: agency-roster
description: >-
  Master roster, search index, and multi-agent team orchestrator for The Agency
  (msitarzewski/agency-agents) — 283 specialized AI agent personas across 18 divisions
  (Engineering, Design, Marketing, Product, Testing, Security, Game Dev, Strategy/NEXUS, etc.).
  Use when the user asks to activate an Agency persona, assemble a multi-agent team,
  run a NEXUS runbook, or search/manage the installed agency-agents collection.
---

# 🎭 The Agency — Master Roster & Orchestrator (`agency-roster`)

All **283 specialized AI agents** across **18 divisions** from `msitarzewski/agency-agents` are installed in `E:\.agents`:
- **Converted Antigravity Skills (`SKILL.md`):** `E:\.agents\agency-skills\agency-<slug>\SKILL.md`
- **Raw Persona Markdown & Strategy Runbooks:** `E:\.agents\agents\agency\`
- **Full Searchable JSON Catalog:** `E:\.agents\agents\agency\catalog.json`
- **Multi-Agent Runbooks & NEXUS Strategy:** `E:\.agents\agents\agency\strategy\runbooks.json` & `E:\.agents\agents\agency\strategy\nexus-strategy.md`

---

## ⚡ 1. Tìm Kiếm & Quản Lý Đội Ngũ Agent (`agency_manager.py`)

Sử dụng CLI quản lý tại [`E:\.agents\tools\agency_manager.py`](file:///E:/.agents/tools/agency_manager.py):

```powershell
# Liệt kê 18 phòng ban (Divisions) và số lượng Agent
python E:\.agents\tools\agency_manager.py --list-divisions

# Tìm kiếm Agent theo từ khóa (chuyên môn, công nghệ, vai trò)
python E:\.agents\tools\agency_manager.py --search "video"
python E:\.agents\tools\agency_manager.py --search "architect"

# Liệt kê toàn bộ Agent thuộc 1 phòng ban
python E:\.agents\tools\agency_manager.py --list-agents --division engineering

# Chỉ kích hoạt một số phòng ban cụ thể trong skills.json (nếu muốn thu gọn context)
python E:\.agents\tools\agency_manager.py --install --filter-divisions "engineering,design,testing,product"

# Kích hoạt lại toàn bộ 283 Agent
python E:\.agents\tools\agency_manager.py --install
```

---

## 🚀 2. Cách Kích Hoạt Agent Trong Antigravity

### Cách A: Kích hoạt trực tiếp như Skill (Single-Agent Persona)
Đọc file `E:\.agents\agency-skills\agency-<slug>\SKILL.md` tương ứng (ví dụ: `agency-frontend-developer`, `agency-backend-architect`, `agency-visual-storyteller`, `agency-reality-checker`) và áp dụng quy trình, tiêu chuẩn đầu ra (deliverables) của chuyên gia đó.

### Cách B: Khởi chạy Đội Ngũ Subagent Độc Lập (`define_subagent` + `invoke_subagent`)
Khi bài toán cần nhiều chuyên gia phối hợp song song (ví dụ: `Software Architect` thiết kế $\to$ `Frontend Developer` & `Backend Architect` code $\to$ `Reality Checker` kiểm thử):
1. Đọc nội dung từ `E:\.agents\agency-skills\agency-<slug>\SKILL.md`.
2. Gọi công cụ `define_subagent` với `Name="agency-<slug>"`, `Description` từ frontmatter, và `SystemPrompt` từ nội dung persona.
3. Gọi `invoke_subagent` để giao task chuyên biệt cho từng subagent chạy song song.

---

## 🏢 3. Danh Mục 18 Phòng Ban (Divisions)

| Division Slug | Tên Phòng Ban | Số Lượng | Lưu Trữ Tại |
| :--- | :--- | :---: | :--- |
| `engineering` | Engineering | 66 | `E:\.agents\agents\agency\engineering\` |
| `specialized` | Specialized | 59 | `E:\.agents\agents\agency\specialized\` |
| `marketing` | Marketing | 37 | `E:\.agents\agents\agency\marketing\` |
| `game-development` | Game Development | 21 | `E:\.agents\agents\agency\game-development\` |
| `gis` | GIS | 13 | `E:\.agents\agents\agency\gis\` |
| `security` | Security | 12 | `E:\.agents\agents\agency\security\` |
| `design` | Design | 10 | `E:\.agents\agents\agency\design\` |
| `sales` | Sales | 9 | `E:\.agents\agents\agency\sales\` |
| `testing` | Testing | 9 | `E:\.agents\agents\agency\testing\` |
| `paid-media` | Paid Media | 7 | `E:\.agents\agents\agency\paid-media\` |
| `project-management` | Project Management | 7 | `E:\.agents\agents\agency\project-management\` |
| `academic` | Academic | 6 | `E:\.agents\agents\agency\academic\` |
| `product` | Product | 6 | `E:\.agents\agents\agency\product\` |
| `spatial-computing` | Spatial Computing | 6 | `E:\.agents\agents\agency\spatial-computing\` |
| `support` | Support | 6 | `E:\.agents\agents\agency\support\` |
| `finance` | Finance | 5 | `E:\.agents\agents\agency\finance\` |
| `healthcare` | Healthcare | 3 | `E:\.agents\agents\agency\healthcare\` |
| `research` | Research | 1 | `E:\.agents\agents\agency\research\` |
