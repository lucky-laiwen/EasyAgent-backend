# PPT 大纲审核与修改功能设计

## 概述

将 PPT 生成流程拆分为两个独立阶段：先生成大纲供用户审核和修改，用户确认后再生成 PPT 幻灯片。用户通过前端结构化表单编辑大纲，修改完成后提交回后端。

## 当前状态

`ppt_stream()` 函数（`utils/openai_client.py:282`）在一个 SSE 流中完成全部工作：
1. 生成大纲（ReAct 工具调用 + Structured Output）
2. 逐页生成 HTML

用户无法在中间介入审核或修改。

## 设计方案

### 架构：3 个独立端点

| 端点 | 类型 | 职责 |
|------|------|------|
| `POST /chat/ppt_outline` | SSE 流 | 生成大纲，存入 DB |
| `POST /chat/update_outline` | REST | 更新用户修改后的大纲 |
| `POST /chat/ppt_generate` | SSE 流 | 从 DB 读取大纲，生成 PPT |

### 数据存储

复用 `tool_calls` 表，通过 `tool_name` 区分：

| 记录 | tool_name | tool_content | status 语义 |
|------|-----------|-------------|------------|
| 大纲 | `ppt_outline` | `{slides: [...], style: {...}}` | 2=待确认, 1=已确认, 0=已取消 |
| PPT | `ppt` | `{slides: [{index, html}]}` | 1=完成, 0=失败 |

两条记录通过 `message_id` 关联到同一条 AI 消息，但数据完全独立，不冗余。

### 状态流转

```
用户请求生成 PPT
  → 大纲生成完成，tool_name="ppt_outline", status=2
  → 前端展示大纲表单

用户修改大纲
  → update_outline 更新 tool_content，status 保持 2

用户确认大纲
  → ppt_generate 读取大纲，将 status 更新为 1
  → 逐页生成 HTML
  → 新建 tool_name="ppt", status=1 的记录
```

## API 详细设计

### 1. `POST /chat/ppt_outline`

**请求体：**
```json
{
  "id": 123,
  "message": "帮我做一个关于人工智能的PPT",
  "doc_ids": [1, 2],
  "file_ids": [3]
}
```

**SSE 事件：**

| 事件 | 数据格式 | 说明 |
|------|---------|------|
| `think` | `{content: "...", type: "think"}` | LLM 思考过程 |
| `tool_start` | `{tool: "...", tool_run_id: "...", args: "...", type: "tool_start"}` | 工具调用开始 |
| `tool_mid` | `{tool: "...", tool_run_id: "...", tool_content: ..., type: "tool_mid"}` | 工具返回结果 |
| `outline` | `{type: "outline", slides: [...], style: {...}}` | 大纲生成完成 |
| `done` | `{done: true}` | 流结束 |
| `error` | `{error: "错误信息"}` | 出错 |

**副作用：**
- 创建 AI 消息（`messages` 表，`sender=1`, `message_type="ppt"`）
- 创建 `tool_calls` 记录（`tool_name="ppt_outline"`, `status=2`）

**实现：** 从 `ppt_stream()` 中提取阶段 1 的逻辑为 `ppt_outline_stream()`。

### 2. `POST /chat/update_outline`

**请求体：**
```json
{
  "message_id": 456,
  "outline": {
    "style": {
      "theme": "dark",
      "primaryColor": "#3B82F6",
      "secondaryColor": "#10B981",
      "textColor": "#FFFFFF",
      "subtextColor": "#D1D5DB",
      "fontFamily": "Inter, sans-serif",
      "titleStyle": "text-4xl font-bold",
      "bodyStyle": "text-lg",
      "cardStyle": "bg-white/10 rounded-xl p-6",
      "backgroundCSS": "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)"
    },
    "slides": [
      {
        "index": 0,
        "title": "封面标题",
        "subtitle": "副标题",
        "description": "本页用于引入主题",
        "layout": "title",
        "points": [],
        "visualSuggestion": "图标: rocket, star"
      }
    ]
  }
}
```

**校验规则：**
- `message_id` 对应的 `ppt_outline` 记录必须存在且 `status=2`
- `slides` 数组不能为空
- `style` 对象必须包含所有必需字段

**响应：**
```json
{"status": 200, "message": "大纲更新成功", "data": null, "success": true}
```

**副作用：** 更新 `tool_calls` 记录的 `tool_content`。

### 3. `POST /chat/ppt_generate`

**请求体：**
```json
{
  "id": 123,
  "message_id": 456
}
```

**流程：**
1. 查询 `tool_calls` 中 `message_id=456 AND tool_name="ppt_outline"` 的记录
2. 校验 `status=2`，否则返回错误
3. 将 `ppt_outline` 的 `status` 更新为 `1`
4. 解析 `tool_content` 获取大纲和样式
5. 逐页调用 LLM 生成 HTML
6. 创建 `tool_name="ppt"` 的记录，保存 HTML 数据

**SSE 事件：**

| 事件 | 数据格式 | 说明 |
|------|---------|------|
| `think` | `{content: "...", type: "think"}` | LLM 思考过程 |
| `slide_start` | `{index: 0, type: "slide_start"}` | 开始生成某页 |
| `slide_chunk` | `{index: 0, content: "<html>...", type: "slide_chunk"}` | HTML 片段 |
| `slide_end` | `{index: 0, type: "slide_end"}` | 某页生成完成 |
| `text` | `{content: "...", type: "text"}` | 总结文本 |
| `done` | `{done: true}` | 流结束 |
| `error` | `{error: "错误信息"}` | 出错 |

**实现：** 从 `ppt_stream()` 中提取阶段 2 的逻辑为 `ppt_slide_stream()`。

## 前端大纲编辑组件数据契约

### 大纲 JSON 结构

```typescript
interface OutlineStyle {
  theme: "dark" | "light" | "gradient";
  primaryColor: string;      // hex
  secondaryColor: string;    // hex
  textColor: string;
  subtextColor: string;
  fontFamily: string;
  titleStyle: string;        // Tailwind classes
  bodyStyle: string;
  cardStyle: string;
  backgroundCSS: string;
}

interface SlideItem {
  index: number;
  title: string;             // 15字以内
  subtitle?: string;
  description: string;       // 一句话概述
  layout: "title" | "content" | "grid" | "split" | "summary";
  points: string[];          // 要点列表
  visualSuggestion?: string; // 推荐的图标/图片
}

interface Outline {
  style: OutlineStyle;
  slides: SlideItem[];
}
```

### 前端操作

- **编辑字段：** 修改任意 slide 的 title/subtitle/description/layout/points/visualSuggestion
- **增删页面：** 添加新 slide、删除已有 slide、拖拽排序
- **编辑样式：** 修改 style 中的颜色、字体等全局样式
- **增删要点：** 在 points 数组中添加/删除条目
- **布局选择：** 下拉选择 title/content/grid/split/summary

### 提交格式

前端将修改后的完整 `Outline` JSON 发送给 `update_outline` 接口，格式与接收时完全一致。

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 大纲生成失败 | 返回 `error` 事件，不创建 DB 记录 |
| 大纲为空（slides=[]） | 返回 `error` 事件 |
| 用户修改后 JSON 格式错误 | `update_outline` 返回 400 |
| 用户修改后 slides 为空 | `update_outline` 返回 400，至少保留 1 页 |
| 大纲确认时记录不存在 | `ppt_generate` 返回 404 |
| 大纲确认时 status 不是 2 | `ppt_generate` 返回 400 |
| PPT 生成中途客户端断开 | 保存已生成的部分 HTML，ppt 记录 status=0 |
| 用户未确认直接关闭页面 | 大纲记录保留 status=2，下次进入可恢复 |
| 用户多次点击确认 | 幂等处理，status 已是 1 则直接返回 |

## 实现范围

### 后端改动

| 文件 | 改动 |
|------|------|
| `router/chat.py` | 新增 `POST /chat/ppt_outline`、`POST /chat/update_outline`、`POST /chat/ppt_generate` 三个端点 |
| `utils/openai_client.py` | 拆分 `ppt_stream()` 为 `ppt_outline_stream()` 和 `ppt_slide_stream()`，原函数保留 |
| `crud/messages.py` | 新增 `get_tool_call_by_message_and_name()` 查询函数 |

### 不改动

- 数据库表结构（复用 `tool_calls` 表，无需 migration）
- `ppt_outline_prompt.md` 和 `ppt_slide_prompt.md` 提示词
- 现有的 `ppt_stream()` 函数（保留兼容）

### 前端配合（不在本次范围内）

- 大纲编辑组件
- 大纲确认/修改按钮
- 调用 `update_outline` 和 `ppt_generate` 接口
