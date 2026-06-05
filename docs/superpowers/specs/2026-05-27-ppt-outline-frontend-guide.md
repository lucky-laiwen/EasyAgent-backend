# PPT 大纲审核功能 - 前端集成指南

## 概述

PPT 生成流程从「一步到位」改为「先大纲后生成」。前端需要新增大纲展示、编辑和确认的交互。

## 新增 API 端点

### 1. `POST /chat/ppt_outline` — 生成大纲（SSE 流）

替代原来的 `POST /chat/stream`（`mode: "ppt"`），只生成大纲，不生成 PPT。

**请求：**
```json
{
  "id": 123,
  "message": "帮我做一个关于人工智能的PPT",
  "doc_ids": [1, 2],
  "file_ids": [3]
}
```

**SSE 事件：**
```javascript
// 思考过程（可选展示）
{ type: "think", content: "..." }

// 工具调用（搜索/天气）
{ type: "tool_start", tool: "web_search", tool_run_id: "...", args: "..." }
{ type: "tool_mid",   tool: "web_search", tool_run_id: "...", tool_content: {...} }

// ★ 大纲生成完成 — 关键事件，用于展示编辑表单
{
  type: "outline",
  style: { theme, primaryColor, secondaryColor, ... },
  slides: [
    {
      index: 0,
      title: "封面标题",
      subtitle: "副标题",
      description: "本页用于引入主题",
      layout: "title",
      points: [],
      visualSuggestion: "图标: rocket, star",
      images: [
        { url: "https://example.com/cover.jpg", type: "web", description: "封面图", position: "main" }
      ]
    },
    {
      index: 1,
      title: "核心内容",
      subtitle: "",
      description: "展示主要观点",
      layout: "content",
      points: ["要点1", "要点2", "要点3"],
      visualSuggestion: "图标: brain, lightbulb; 图片: https://example.com/ai.jpg",
      images: [
        { url: "https://example.com/ai.jpg", type: "web", description: "AI", position: "main" }
      ]
    }
  ]
}

// 流结束
{ done: true }
```

**收到 `outline` 事件后，前端应：**
1. 关闭 SSE 连接
2. 解析 outline 数据，展示大纲编辑表单
3. 隐藏聊天输入框（或切换为大纲操作按钮）

---

### 2. `POST /chat/update_outline` — 更新大纲（REST）

用户在前端编辑大纲后，提交修改。

**请求：**
```json
{
  "message_id": 456,
  "outline": {
    "style": { ... },
    "slides": [ ... ]
  }
}
```

- `message_id`：大纲所属的 AI 消息 ID（从 `ppt_outline` SSE 的响应中获取）
- `outline`：修改后的完整大纲 JSON，格式与收到的 `outline` 事件一致

**响应：**
```json
// 成功
{ "status": 200, "message": "大纲更新成功", "data": null, "success": true }

// 失败：记录不存在或已确认
{ "status": 400, "message": "大纲记录不存在或已确认", "data": null, "success": false }

// 失败：slides 为空
{ "status": 400, "message": "至少需要保留一页幻灯片", "data": null, "success": false }
```

**注意：** 修改时不需要调用此接口，可以在用户点「确认生成」时一次性提交修改后的大纲。

---

### 3. `POST /chat/ppt_generate` — 生成 PPT（SSE 流）

用户确认大纲后，触发 PPT 生成。

**请求：**
```json
{
  "id": 123,
  "message_id": 456
}
```

- `id`：chat_id
- `message_id`：大纲所属的 AI 消息 ID

**SSE 事件：**
```javascript
// 思考过程
{ type: "think", content: "..." }

// 某页开始生成
{ type: "slide_start", index: 0 }

// HTML 片段（流式拼接）
{ type: "slide_chunk", index: 0, content: "<!DOCTYPE html>..." }

// 某页生成完成
{ type: "slide_end", index: 0 }

// 总结文本
{ type: "text", content: "已为你生成 5 页 PPT..." }

// 流结束
{ done: true }
```

这与原来 `POST /chat/stream`（`mode: "ppt"`）中阶段 2 的事件格式完全一致，前端已有的 PPT 渲染逻辑可以直接复用。

---

## 前端交互流程

```
用户: "帮我做一个关于AI的PPT"
  │
  ▼
前端: POST /chat/ppt_outline（SSE）
  │
  ├── think/tool_start/tool_mid 事件 → 正常展示
  │
  ├── outline 事件 → ★ 展示大纲编辑表单
  │     │
  │     ▼
  │   用户查看大纲
  │     │
  │     ├── 点击「修改」→ 进入编辑模式
  │     │     │
  │     │     ├── 修改标题/要点/布局/样式...
  │     │     ├── 可选：提交修改 POST /chat/update_outline
  │     │     └── 继续编辑或确认
  │     │
  │     └── 点击「确认生成」→ POST /chat/ppt_generate（SSE）
  │           │
  │           ├── slide_start/chunk/end 事件 → 渲染 PPT
  │           └── done 事件 → 完成
  │
  └── done 事件（大纲生成结束）
```

## 大纲编辑组件设计建议

### 数据结构

```typescript
interface OutlineStyle {
  theme: "dark" | "light" | "gradient";
  primaryColor: string;
  secondaryColor: string;
  textColor: string;
  subtextColor: string;
  fontFamily: string;
  titleStyle: string;
  bodyStyle: string;
  cardStyle: string;
  backgroundCSS: string;
}

interface SlideImage {
  url: string;                           // 图片 URL
  type: "web" | "upload" | "placeholder"; // 来源类型
  description: string;                   // 图片描述
  position: "main" | "background" | "icon"; // 图片位置
}

interface SlideItem {
  index: number;
  title: string;             // 15字以内
  subtitle?: string;
  description: string;
  layout: "title" | "content" | "grid" | "split" | "summary";
  points: string[];
  visualSuggestion?: string;
  images?: SlideImage[];     // 本页图片列表，可渲染和替换
}

interface Outline {
  style: OutlineStyle;
  slides: SlideItem[];
}
```

### 编辑功能

| 功能 | 说明 |
|------|------|
| 编辑标题 | 直接点击 title 文字，inline 编辑或弹窗 |
| 编辑要点 | points 列表的增删改，每项可独立编辑 |
| 修改布局 | 下拉选择：title / content / grid / split / summary |
| 增删页面 | 添加新页、删除已有页、拖拽排序 |
| 编辑样式 | 修改全局颜色/字体（可折叠面板） |
| 修改副标题 | subtitle 字段编辑 |
| 视觉建议 | visualSuggestion 字段编辑 |
| 替换图片 | 点击 `images` 中的图片缩略图 → 搜索新图或上传 → 替换 url，提交时随 slides 一起传回 |

### 布局类型说明

| 布局 | 适用场景 | 视觉特征 |
|------|---------|---------|
| `title` | 封面/结尾 | 居中大标题 + 副标题 |
| `content` | 文字为主 | 标题 + 要点列表 |
| `grid` | 多项并列 | 2x2 或 3 列卡片 |
| `split` | 图文并排 | 左文字 + 右图片 |
| `summary` | 总结回顾 | 关键要点高亮 |

### 推荐 UI 方案

**方案 A：列表卡片式**
- 每页幻灯片渲染为一个卡片
- 卡片内显示标题、要点预览、布局图标
- 点击卡片展开编辑面板
- 支持拖拽排序

**方案 B：左右分栏式**
- 左侧：幻灯片缩略图列表（可拖拽排序）
- 右侧：选中页的编辑表单
- 底部：全局样式编辑

**方案 C：弹窗表单式**
- 大纲以预览形式展示
- 点击「编辑」弹出全屏表单弹窗
- 弹窗内完成所有编辑操作

## 消息存储变化

原来 `mode: "ppt"` 会在 `messages` 表创建一条 `message_type="ppt"` 的 AI 消息，`tool_calls` 表创建一条 `tool_name="ppt"` 的记录。

现在拆分为：

| 阶段 | messages 表 | tool_calls 表 |
|------|------------|--------------|
| 大纲生成 | 创建 AI 消息（`message_type="ppt"`） | 创建 `tool_name="ppt_outline"`, `status=2` |
| 大纲更新 | 不变 | 更新 `tool_content` |
| PPT 生成 | 不变 | 创建 `tool_name="ppt"`, `status=1` |

**前端获取消息列表时**，需要识别 `tool_name="ppt_outline"` 的记录，展示大纲预览而非最终 PPT。

## 加载已有大纲（页面刷新/重新进入）

用户刷新页面或重新进入聊天时，需要从消息列表恢复大纲状态。

**判断逻辑：**
1. 获取聊天消息列表 `GET /chat/get_chat_message/{chat_id}`
2. 遍历每条消息的 `tool_calls`
3. 如果存在 `tool_name="ppt_outline"` 且 `status=2` → 展示大纲编辑表单
4. 如果存在 `tool_name="ppt"` 且 `status=1` → 展示最终 PPT
5. 如果两者都存在，优先展示最终 PPT

## 图片替换流程

大纲中的 `images` 字段由后端自动从 `visualSuggestion` 中解析提取。前端可以展示图片缩略图，允许用户替换。

**替换流程：**
1. 前端展示 `images` 中的图片缩略图（`url` 字段）
2. 用户点击某张图片 → 弹出搜索面板或上传入口
3. 用户选择新图片后，更新对应 `images` 项的 `url`（`type` 改为 `"upload"` 或保持 `"web"`）
4. 用户点击「确认生成」时，`images` 随 `slides` 一起通过 `update_outline` 提交
5. 后端生成 HTML 时，优先使用 `images` 中的 URL 替代 `visualSuggestion` 中的原始 URL

**前端展示建议：**
- `split` 布局：右侧图片区域展示 `images` 中 `position="main"` 的图片
- `title` 布局：背景区域展示 `position="background"` 的图片
- `grid` 布局：每个卡片展示对应的图片
- 没有 `images` 或为空时，显示占位区域，提示用户可添加图片

## 注意事项

1. **message_id 获取**：`ppt_outline` SSE 流结束时，需要额外返回 `message_id`，或者前端从消息列表中查询最新的 AI 消息。建议后端在 `done` 事件中附带 `message_id`。

2. **取消操作**：用户在大纲编辑阶段关闭聊天，大纲数据会保留在数据库中（`status=2`），下次进入可恢复。

3. **并发控制**：用户快速连续点击「确认生成」时，后端做了幂等处理（status 已是 1 直接返回），前端也应做防抖。

4. **样式编辑**：`style` 对象中的 Tailwind classes 字段（`titleStyle`、`bodyStyle`、`cardStyle`）对普通用户不友好，建议前端提供预设主题选择，而非直接编辑 Tailwind 类名。
