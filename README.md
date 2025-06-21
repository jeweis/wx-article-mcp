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

请将示例中的占位符替换为您的实际数据库连接信息，并根据 Cline 的具体配置格式进行调整。

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

### 测试

测试