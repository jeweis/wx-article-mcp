# 微信公众号文章保存 MCP Server

这是一个MCP服务器，提供了以下功能：

- 保存微信公众号文章到公众号草稿


## MCP 配置

本项目支持通过多种客户端配置 MCP 服务器，以便与各种 IDE 或工具集成。以下是一些常见客户端的配置示例：

### Windsurf / Cursor / Claude

对于基于 Windsurf 框架的客户端（如 Cursor 和 Claude），您可以在 `~/.codeium/windsurf/mcp_config.json` 文件中配置 MCP 服务器。以下是一个示例配置：

```json
{
  "mcpServers": {
    "wx-article-mcp": {
      "command": "uvx",
      "args": [
        "wx-article-mcp"
      ],
      "env": {
        "WXMP_APPID": "填公众号appId",
        "WXMP_SECRET": "填公众号密钥"
      }
    }
  }
}
```


### Cline

对于 Cline 客户端，您可以在其配置文件中添加类似的 MCP 服务器配置。具体的配置方式请参考 Cline 的官方文档。通常，您需要指定服务器的名称、命令、参数和环境变量。

```json
// Cline 配置文件示例 (具体格式请参考 Cline 文档)
{
  "mcpServers": {
    "wx-article-mcp": {
      "command": "uvx",
      "args": [
        "wx-article-mcp"
      ],
      "env": {
        "WXMP_APPID": "填公众号appId",
        "WXMP_SECRET": "填公众号密钥"
      }
    }
  }
}
```

请将示例中的占位符替换为您的实际信息，并根据 Cline 的具体配置格式进行调整。

### 配置ip白名单
#### 使用前需要在公众号后台配置ip白名单哦
![1750647674747_d](https://github.com/user-attachments/assets/c2a74c20-2d13-436c-9b38-f6c8b9e85800)


## 以下是源码方式使用

## 安装

1. 克隆仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 配置环境变量（参见下文）

## 配置

在项目根目录创建`.env`文件，包含以下环境变量：

```
WXMP_APPID=wxxxx
WXMP_SECRET=xxx
```

## 运行

### 使用uvx安装并运行（推荐）

```bash
uvx wx-article-mcp
```

### 或者从源码运行

```bash
python -m server.py
```

## 功能

### 微信公众号文章管理
- 保存微信公众号文章到公众号草稿
- 支持富文本内容处理
- 自动处理图片上传和媒体资源管理

### Markdown 支持
- 完整的 Markdown 语法支持
- 代码高亮显示
- **Mermaid 图表支持**：支持在 Markdown 中使用 Mermaid 语法创建各种图表
  - 流程图 (Flowchart)
  - 序列图 (Sequence Diagram)
  - 甘特图 (Gantt Chart)
  - 类图 (Class Diagram)
  - 状态图 (State Diagram)
  - 饼图 (Pie Chart)
  - 等等...

#### Mermaid 图表使用示例

在 Markdown 中使用 Mermaid 图表非常简单，只需要使用 `mermaid` 代码块：

````markdown
```mermaid
graph TD
    A[开始] --> B{是否登录?}
    B -->|是| C[显示主页]
    B -->|否| D[跳转登录页]
    D --> E[用户登录]
    E --> C
    C --> F[结束]
```
````

上述代码将生成一个流程图，系统会自动将 Mermaid 图表渲染为图片并上传到微信公众号，确保在文章中正常显示。

