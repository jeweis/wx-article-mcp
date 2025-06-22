#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
微信公众号MCP服务器
实现以下功能：
1. 保存微信公众号文章到草稿（包含图片上传和保存后自动删除素材）
"""

import os
import json
import time
import requests
import markdown
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import asyncio
import concurrent.futures
from mermaid_cli import render_mermaid

# 加载环境变量
load_dotenv()

# Mermaid图表渲染函数
async def _async_render_mermaid(mermaid_code: str):
    """异步渲染Mermaid图表为PNG图片并上传到微信"""
    import hashlib
    import os
    
    # 生成基于内容的文件名
    content_hash = hashlib.md5(mermaid_code.encode()).hexdigest()[:8]
    img_filename = f"mermaid_{content_hash}.png"
    img_path = os.path.join("img", img_filename)
    
    # 确保img目录存在
    os.makedirs("img", exist_ok=True)
    
    # 渲染Mermaid图表为PNG
    title, desc, png_data = await render_mermaid(
        mermaid_code,
        output_format="png",
        background_color="white",
        mermaid_config={"theme": "default"}
    )
    
    # 保存PNG文件到本地
    with open(img_path, 'wb') as f:
        f.write(png_data)
    
    # 上传图片到微信并获取media_id
    try:
        result = await image_to_media_id(img_path, None, None)
        wx_image_url = result.get("url", "")
        
        # 删除本地临时文件
        if os.path.exists(img_path):
            os.remove(img_path)
            
        return wx_image_url
    except Exception as e:
        print(f"上传微信图片失败: {e}")
        # 如果上传失败，返回本地路径
        return img_path

def render_mermaid_to_image(mermaid_code: str) -> str:
    """
    将Mermaid代码渲染为PNG图片并上传到微信
    
    Args:
        mermaid_code: Mermaid图表代码
        
    Returns:
        微信图片的HTML标签
    """
    try:
        # 使用线程池执行器来避免事件循环冲突
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                lambda: asyncio.run(_async_render_mermaid(mermaid_code))
            )
            wx_image_url = future.result(timeout=30)  # 30秒超时
            
            # 如果获取到微信图片URL，返回微信图片HTML标签
            if wx_image_url and wx_image_url.startswith('http'):
                return f'<img src="{wx_image_url}" alt="Mermaid图表" style="max-width: 100%; height: auto;">'
            else:
                # 如果是本地路径，返回相对路径
                return f'<img src="/{wx_image_url}" alt="Mermaid图表" style="max-width: 100%; height: auto;">'
            
    except Exception as e:
        print(f"Mermaid渲染错误: {e}")
        # 如果渲染失败，返回原始代码块
        return f'<pre><code class="language-mermaid">{mermaid_code}</code></pre>'

# 微信公众号配置
WXMP_APPID = os.getenv("WXMP_APPID")
WXMP_SECRET = os.getenv("WXMP_SECRET")

# 创建MCP服务器
mcp = FastMCP(name="微信公众号MCP服务器", dependencies=[])

# 配置信息
class WxConfig:
    """微信公众号配置信息"""
    appid = WXMP_APPID
    secret = WXMP_SECRET
    token_file = "access_token.json"
    
    @classmethod
    def check_config(cls):
        """检查配置是否完整"""
        if not cls.appid or not cls.secret:
            raise ValueError("请设置环境变量WXMP_APPID和WXMP_SECRET")

# 获取微信access_token
def get_access_token(force_refresh=False) -> str:
    """
    获取微信公众号access_token
    
    Args:
        force_refresh: 是否强制刷新token
        
    Returns:
        access_token: 微信公众号access_token
    """
    WxConfig.check_config()
    
    # 检查本地token是否存在且有效
    if not force_refresh and os.path.exists(WxConfig.token_file):
        try:
            with open(WxConfig.token_file, "r") as f:
                token_info = json.load(f)
                if token_info.get("expires_time", 0) > time.time():
                    return token_info["access_token"]
        except Exception:
            pass
    
    # 获取新token
    url = "https://api.weixin.qq.com/cgi-bin/stable_token"
    data = {
        "grant_type": "client_credential",
        "appid": WxConfig.appid,
        "secret": WxConfig.secret,
        "force_refresh": force_refresh
    }
    
    response = requests.post(url, json=data)
    result = response.json()
    
    if "access_token" in result:
        # 保存token到本地
        token_info = {
            "access_token": result["access_token"],
            "expires_in": result["expires_in"],
            "expires_time": int(time.time() + result["expires_in"] - 300)  # 提前5分钟过期
        }
        
        with open(WxConfig.token_file, "w") as f:
            json.dump(token_info, f)
            
        return result["access_token"]
    else:
        raise Exception(f"获取access_token失败: {result}")

# 封装图片转微信media_id的方法
async def image_to_media_id(url: str, access_token: str | None, ctx: Context | None) -> Dict[str, str]:
    """
    将图片转换为微信公众号素材ID(media_id)
    
    Args:
        url: 图片URL地址或本地文件路径
        access_token: 可选的access_token，如果不提供则自动获取
        ctx: 可选的上下文对象，用于输出日志
        
    Returns:
        包含media_id的字典
    """
    log_info = lambda msg: ctx.info(msg) if ctx else None
    log_error = lambda msg: ctx.error(msg) if ctx else None
    
    # 如果URL为空，返回报错
    if not url:
        log_info and log_info("未提供封面图片URL")
        raise Exception("未提供封面图片URL")
        
    
    log_info and log_info(f"开始处理图片: {url}")
    
    try:
        # 判断是网络URL还是本地文件路径
        if url.startswith(('http://', 'https://')):
            # 网络URL，下载图片
            log_info and log_info("正在下载网络图片...")
            image_response = requests.get(url, stream=True)
            if image_response.status_code != 200:
                raise Exception(f"下载图片失败，状态码: {image_response.status_code}")
            image_content = image_response.content
            # 从URL推断文件名
            filename = url.split('/')[-1] if '/' in url else 'image.jpg'
            if '.' not in filename:
                filename = 'image.jpg'
        else:
            # 本地文件路径
            log_info and log_info("正在读取本地图片...")
            if not os.path.exists(url):
                raise Exception(f"本地图片文件不存在: {url}")
            with open(url, 'rb') as f:
                image_content = f.read()
            filename = os.path.basename(url)
        
        # 获取access_token
        if not access_token:
            log_info and log_info("获取微信access_token...")
            access_token = get_access_token()
        
        # 上传图片到微信服务器
        log_info and log_info("上传图片到微信服务器...")
        upload_url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type=image"
        
        # 根据文件扩展名确定MIME类型
        mime_type = 'image/jpeg'
        if filename.lower().endswith('.png'):
            mime_type = 'image/png'
        elif filename.lower().endswith('.gif'):
            mime_type = 'image/gif'
        
        files = {'media': (filename, image_content, mime_type)}
        upload_response = requests.post(upload_url, files=files)
        result = upload_response.json()
        
        if "media_id" not in result:
            raise Exception(f"上传图片失败: {result}")
        
        log_info and log_info(f"图片上传成功，media_id: {result['media_id']}")
        return {
            "media_id": result["media_id"],
            "url": result.get("url")
        }
        
    except Exception as e:
        error_msg = f"图片转换失败: {str(e)}"
        log_error and log_error(error_msg)
        raise Exception(error_msg)

# 封装上传图文消息内的图片获取URL的方法
async def upload_article_image(url: str, access_token: str | None, ctx: Context | None) -> str:
    """
    上传图文消息内的图片获取URL
    
    Args:
        url: 图片URL地址
        access_token: 可选的access_token，如果不提供则自动获取
        ctx: 可选的上下文对象，用于输出日志
        
    Returns:
        图片的微信URL
    """
    log_info = lambda msg: ctx.info(msg) if ctx else None
    log_error = lambda msg: ctx.error(msg) if ctx else None
    
    # 如果URL为空，返回默认图片URL
    if not url:
        log_info and log_info("未提供图片URL，跳过处理")
        return ""
    
    log_info and log_info(f"开始上传文章内图片: {url}")
    
    try:
        # 下载图片
        log_info and log_info("正在下载图片...")
        image_response = requests.get(url, stream=True)
        if image_response.status_code != 200:
            raise Exception(f"下载图片失败，状态码: {image_response.status_code}")
        
        # 获取access_token
        if not access_token:
            log_info and log_info("获取微信access_token...")
            access_token = get_access_token()
        
        # 上传图片到微信服务器
        log_info and log_info("上传图文消息内的图片...")
        upload_url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={access_token}"
        
        files = {'media': ('image.jpg', image_response.content, 'image/jpeg')}
        upload_response = requests.post(upload_url, files=files)
        result = upload_response.json()
        
        if "url" not in result:
            raise Exception(f"上传图文消息内的图片失败: {result}")
        
        log_info and log_info(f"图文消息内的图片上传成功，url: {result['url']}")
        return result["url"]
        
    except Exception as e:
        error_msg = f"上传图文消息内的图片失败: {str(e)}"
        log_error and log_error(error_msg)
        raise Exception(error_msg)

# 处理HTML内容中的图片URL
async def process_html_images(html_content: str, access_token: str = None, ctx: Context = None) -> str:
    """
    处理HTML内容中的图片URL，将外部图片URL转换为微信的URL
    
    Args:
        html_content: HTML内容
        access_token: 可选的access_token，如果不提供则自动获取
        ctx: 可选的上下文对象，用于输出日志
        
    Returns:
        处理后的HTML内容
    """
    import re
    from bs4 import BeautifulSoup
    
    log_info = lambda msg: ctx.info(msg) if ctx else None
    
    # 如果内容为空，直接返回
    if not html_content:
        log_info and log_info("文章内容为空，跳过图片处理")
        return html_content
    
    try:
        log_info and log_info("开始处理HTML内容中的图片...")
        
        # 解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找所有图片标签
        img_tags = soup.find_all('img')
        log_info and log_info(f"找到{len(img_tags)}个图片标签")
        
        # 如果没有图片标签，直接返回原内容
        if not img_tags:
            log_info and log_info("文章内容中没有图片，跳过图片处理")
            return html_content
        
        # 处理每个图片
        for img in img_tags:
            src = img.get('src')
            if src and not src.startswith('http://mmbiz.qpic.cn') and not src.startswith('https://mmbiz.qpic.cn'):
                try:
                    # 上传图片到微信服务器并获取URL
                    log_info and log_info(f"处理图片: {src}")
                    wx_url = await upload_article_image(src, access_token, ctx)
                    # 替换图片URL
                    if wx_url:  # 只有当得到有效的URL时才进行替换
                        img['src'] = wx_url
                        log_info and log_info(f"图片URL已替换为微信URL: {wx_url}")
                except Exception as e:
                    log_info and log_info(f"处理图片失败，保留原始图片URL: {str(e)}")
        
        # 返回处理后的HTML
        return str(soup)
    except Exception as e:
        log_info and log_info(f"处理HTML内容中的图片失败: {str(e)}，返回原内容")
        return html_content


@mcp.tool()
async def save_article(
    ctx: Context,
    title: str = Field(..., description="文章标题"),
    content: str = Field(..., description="文章内容，使用Markdown格式编写，支持内容中的图片网络URL，内容中的图片网络URL会自动转换为微信图片URL"),
    thumb_image_url: str = Field("", description="封面图片URL，网络图片地址，选填"),
    author: str = Field("", description="作者"),
    digest: str = Field("", description="文章摘要"),
    content_source_url: str = Field("", description="原文链接"),
    need_open_comment: int = Field(1, description="是否打开评论，0不打开，1打开。")
) -> str:
    """
    保存微信公众号文章到草稿
    
    Args:
        title: 文章标题
        thumb_image_url: 封面图片URL
        author: 作者
        digest: 文章摘要
        content: 文章内容
        content_source_url: 原文链接
        need_open_comment: 是否打开评论
        ctx: 上下文对象
        
    Returns:
        保存结果信息
    """
    await ctx.info(f"开始保存文章: {title}")
    ## 是否粉丝才可评论，0所有人可评论，1粉丝才可评论。现在固定为所有人可以评论，因为一般都设置为0，后续可能考虑支持其他情况
    only_fans_can_comment=0
    
    # 验证标题长度，微信公众号文章标题不能超过64个字符
    if len(title) > 64:
        error_msg = f"文章标题长度超过微信公众号限制，当前长度: {len(title)}，最大长度: 64"
        await ctx.error(error_msg)
        raise Exception(error_msg)
    
    try:
        # 获取access_token
        await ctx.info("获取微信access_token...")
        access_token = get_access_token()
        
        # 先上传封面图片获取media_id
        await ctx.info(f"处理封面图片: {thumb_image_url}")
        ## 如果thumb_image_url为空，使用默认图片
        if not thumb_image_url or not thumb_image_url.strip():
            # 使用默认图片
            default_image_path = os.path.join(os.path.dirname(__file__), "img", "jewei-cat.jpg")
            await ctx.info(f"使用默认封面图片: {default_image_path}")
            image_result = await image_to_media_id(default_image_path, access_token, ctx)
        else:
            image_result = await image_to_media_id(thumb_image_url, access_token, ctx)
        
        thumb_media_id = image_result["media_id"]
        thumb_url = image_result.get("url")
        await ctx.info(f"封面图片处理成功，media_id: {thumb_media_id}, url: {thumb_url}")
        
        # 将Markdown内容转换为HTML
        await ctx.info("将Markdown内容转换为HTML...")
        
        # 使用标准的markdown扩展，不添加自定义样式（移除extra和toc避免生成a标签，extra包含footnotes会生成链接）
        md_extensions = [
            'codehilite',  # 代码高亮
            'fenced_code',  # 围栏代码块
            'tables',  # 表格支持
            'nl2br',  # 换行转换
            'attr_list',  # 属性列表支持
            'def_list',  # 定义列表支持
            'pymdownx.superfences'  # 支持Mermaid图表
        ]
        
        # 配置代码高亮和Mermaid支持
        extension_configs = {
            'codehilite': {
                'use_pygments': True,
                'noclasses': True,  # 使用内联样式
                'css_class': 'highlight'
            },
            'pymdownx.superfences': {
                'custom_fences': [
                    {
                        'name': 'mermaid',
                        'class': 'mermaid',
                        'format': lambda source, language, css_class, options, md, **kwargs: render_mermaid_to_image(source)
                    }
                ]
            }
        }
        
        # 直接转换markdown为HTML，不添加额外样式
        html_content = markdown.markdown(
            content, 
            extensions=md_extensions,
            extension_configs=extension_configs
        )
        
        await ctx.info("Markdown转换为HTML完成，使用原生样式")
        
        # 处理文章内容中的图片URL
        await ctx.info("处理文章内容中的图片URL...")
        processed_content = await process_html_images(html_content, access_token, ctx)
        await ctx.info("文章内容中的图片URL处理完成")
        
        # 创建草稿
        await ctx.info("创建文章草稿...")
        draft_url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}"
        article={
                    "title": title,
                    "author": author,
                    "digest": digest,
                    "content": processed_content,  # 使用处理后的内容
                    "content_source_url": content_source_url,
                    "need_open_comment": need_open_comment,
                    "only_fans_can_comment": only_fans_can_comment
                }
        # 现在总是有封面图片（要么是用户提供的，要么是默认图片）
        article["thumb_media_id"] = thumb_media_id
        draft_data = {
            "articles": [
                article
            ]
        }

        ## 打印draft_data字符串
        print(json.dumps(draft_data, ensure_ascii=False))
        
        draft_response = requests.post(draft_url, data=bytes(json.dumps(draft_data, ensure_ascii=False), encoding='utf-8'))
        await ctx.info(f"draft_response: {draft_response}  draft_data:{draft_data}")
        draft_result = draft_response.json()
        
        if "media_id" not in draft_result:
            raise Exception(f"创建草稿失败: {draft_result}")
        
        media_id = draft_result["media_id"]
        await ctx.info(f"草稿创建成功，media_id: {media_id}")
        
        # 保存成功后删除封面图片素材
        await ctx.info("尝试删除封面图片素材...")
        try:
            # 直接使用上传图片时返回的media_id删除素材
            delete_result = await delete_material(thumb_media_id, access_token, ctx)
            await ctx.info(f"封面图片素材删除结果: {delete_result}")
        except Exception as e:
            await ctx.warning(f"删除封面图片素材失败，但不影响文章保存: {str(e)}")
        
        return f"新增草稿成功，草稿media_id: {media_id}"
        
    except Exception as e:
        await ctx.error(f"保存文章失败: {str(e)}")
        raise



# 封装删除素材的方法
async def delete_material(media_id: str, access_token: str = None, ctx: Context = None) -> Dict[str, Any]:
    """
    删除微信公众号永久素材
    
    Args:
        media_id: 要删除的素材的media_id
        access_token: 可选的access_token，如果不提供则自动获取
        ctx: 可选的上下文对象，用于输出日志
        
    Returns:
        包含errcode和errmsg的字典
    """
    log_info = lambda msg: ctx.info(msg) if ctx else None
    log_error = lambda msg: ctx.error(msg) if ctx else None
    
    try:
        # 获取access_token
        if not access_token:
            log_info and log_info("获取微信access_token...")
            access_token = get_access_token()
        
        log_info and log_info(f"开始删除素材: {media_id}")
        
        # 删除素材
        log_info and log_info("删除素材...")
        delete_url = f"https://api.weixin.qq.com/cgi-bin/material/del_material?access_token={access_token}"
        
        delete_data = {
            "media_id": media_id
        }
        
        delete_response = requests.post(delete_url, json=delete_data)
        delete_result = delete_response.json()
        
        if delete_result.get("errcode", -1) != 0:
            raise Exception(f"删除素材失败: {delete_result}")
        
        log_info and log_info(f"素材删除成功")
        return {
            "errcode": delete_result.get("errcode", 0),
            "errmsg": delete_result.get("errmsg", "ok")
        }
        
    except Exception as e:
        error_msg = f"删除素材失败: {str(e)}"
        log_error and log_error(error_msg)
        raise Exception(error_msg)
def main():
    """主函数，用于启动MCP服务器"""
    print("启动 MySQL MCP 服务器...")
    mcp.run()
if __name__ == "__main__":
    # 运行MCP服务器
    main()
    # mcp.run(transport="streamable-http", host="127.0.0.1", port=8080, path="/mcp")
