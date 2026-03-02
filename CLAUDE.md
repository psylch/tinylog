# TinyLog - LLM 对话查看器与分析看板

> **仓库**: psylch/tinylog
> **技术栈**: Python (FastAPI + SQLite) + React SPA (Vite, 纯 vanilla CSS)

---

## 项目概览

TinyLog 是一个轻量级 LLM 对话日志查看器，支持：
- Dashboard 面板：会话数/消息数/Token/TTFT 统计 + 趋势图表
- Sessions 列表：搜索、分页、详情抽屉（含 tool call 展开）
- Files 管理：图片网格预览 + Lightbox

数据源：读取 Agno 框架的 `agno_sessions.db` SQLite 数据库。

---

## 仓库结构

```
tinylog/
├── tinylog/                    # Python 后端
│   ├── app.py                  # FastAPI 入口
│   ├── cli.py                  # CLI 启动命令
│   ├── config.py               # 配置管理
│   ├── db.py                   # SQLite 查询层
│   ├── api/                    # API 路由
│   ├── services/               # 业务逻辑
│   └── sources/                # 数据源适配
├── frontend/                   # React 前端
│   ├── vite.config.ts          # Vite 配置（纯 react plugin，无 Tailwind）
│   ├── src/
│   │   ├── App.tsx             # 路由 + 认证门控
│   │   ├── styles/index.css    # 完整设计系统（唯一样式文件）
│   │   ├── components/         # Layout, StatCard, SessionDrawer, LoginGate
│   │   ├── pages/              # DashboardPage, SessionsPage, FilesPage
│   │   ├── hooks/useTheme.ts   # 主题切换 (data-theme dark/light)
│   │   ├── services/api.ts     # API 客户端
│   │   ├── types.ts            # TypeScript 类型
│   │   └── utils.ts            # 格式化工具
│   └── index.html
├── pyproject.toml
└── CLAUDE.md                   # 本文件
```

---

## 设计系统（关键约定）

### 零框架纯 CSS

**已移除 Tailwind CSS。** 所有样式在 `frontend/src/styles/index.css` 中，使用 CSS 变量 + 语义化 class。

### 主题变量

通过 `<html data-theme="dark|light">` 切换，所有颜色/阴影/边框为 CSS 变量：

| 变量 | 用途 |
|------|------|
| `--bg-base` / `--bg-surface` / `--bg-elevated` | 三层背景层级 |
| `--bg-hover` / `--bg-hover-strong` | 交互悬停态 |
| `--text-primary` / `--text-secondary` / `--text-muted` | 三级文字 |
| `--accent` / `--accent-hover` / `--accent-muted` | 主色（暗: indigo #5e6ad2，亮: #4f46e5） |
| `--success` / `--danger` / `--warning` + `-muted` | 语义色 |
| `--border` / `--border-light` / `--border-focus` | 边框 |
| `--shadow-sm` / `--shadow-md` / `--shadow-lg` / `--shadow-header` | 阴影层级 |

### 核心 CSS class

| Class | 用途 |
|-------|------|
| `.card` | 卡片容器（12px 圆角，border + shadow-sm，hover 升级到 shadow-md） |
| `.header-glass` | 毛玻璃 sticky header（backdrop-filter blur） |
| `.header-content` / `.main-content` | 居中布局容器（max-width: 1200px） |
| `.nav-link` / `.nav-link.active` | 导航链接 |
| `.btn` / `.btn-primary` / `.btn-secondary` / `.btn-ghost` | 按钮体系 |
| `.input-field` | 表单输入框（focus 带 accent ring） |
| `.table-container` + `.premium-table` | 表格容器 |
| `.badge` | 状态徽章 |
| `.notice` | 错误/警告提示 |
| `.grid-4` / `.grid-2` | 响应式网格 |
| `.skeleton` | 加载骨架屏（shimmer 动画） |
| `.drawer-overlay` / `.drawer-panel` / `.drawer-header` / `.drawer-content` | 抽屉组件 |
| `.msg-bubble` / `.msg-user` / `.msg-ai` | 聊天气泡 |
| `.tool-card` / `.tool-card-header` / `.tool-card-body` | Tool call 展开卡片 |
| `.lightbox-overlay` | 图片预览遮罩 |

### 文字 & 布局工具类

手写了基础工具类（`.text-xs`~`.text-2xl`, `.font-medium`, `.font-semibold`, `.text-primary/secondary/muted`, `.flex`, `.items-center`, `.gap-*`, `.truncate`）。**不是 Tailwind，是纯 CSS。**

### 动画

- `fadeIn`: 淡入
- `fadeUp`: 上滑淡入（聊天气泡）
- `slideIn`: 右侧滑入（抽屉）
- `shimmer`: 骨架屏扫光

### 过渡曲线

统一使用 `cubic-bezier(0.16, 1, 0.3, 1)`（spring-like easing）。

---

## 开发命令

### 后端

```bash
cd tinylog
uv run tinylog --db /path/to/agno_sessions.db --port 7891
# 或直接
uv run uvicorn tinylog.app:app --host 0.0.0.0 --port 7891
```

### 前端

```bash
cd frontend
npm install
npm run dev          # Vite dev → 自动找可用端口
npm run build        # 生产构建 → dist/
```

Vite proxy 配置在 `vite.config.ts`，`/api` 代理到后端端口。

### 前后端联调

1. 启动后端（指定 db 文件和端口）
2. 确认 `vite.config.ts` 中 proxy target 端口一致
3. `npm run dev` 启动前端

---

## 修改注意事项

1. **不要引入 Tailwind** — 已刻意移除，使用纯 CSS 变量 + 语义 class
2. **样式只改 `index.css`** — 所有样式集中在这一个文件
3. **新组件遵循现有 class 命名** — 用 `.card`, `.btn-*`, `.input-field` 等已有 class
4. **CSS 变量命名规范** — `--bg-*`, `--text-*`, `--shadow-*`, `--border-*`, `--accent-*`
5. **所有颜色都用变量** — 不要硬编码颜色值（除了 rgba 透明度变体）
6. **图表（Recharts）的 tooltip/grid 也用 CSS 变量** — 确保深浅主题一致

---

## API 概览

| 端点 | 用途 |
|------|------|
| `GET /api/config` | 应用配置（是否需要认证） |
| `GET /api/overview?period=7d` | 统计概览 + 趋势 |
| `GET /api/daily?from=&to=` | 日级指标（图表数据） |
| `GET /api/tool-stats?from=&to=` | Tool 调用统计 |
| `GET /api/sessions?page=&page_size=&keyword=` | 会话分页列表 |
| `GET /api/sessions/:id` | 会话详情（含消息和 tool calls） |
| `GET /api/files?page=&page_size=` | 文件列表 |
| `GET /api/files/:id` | 文件下载/预览 |

认证：需要时通过 `X-Admin-Key` header 传递。
