# sina_news_plugin.py
"""
新浪财经新闻爬取插件
用于扣子（Coze）平台的插件，可以爬取指定股票代码的新浪财经新闻
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

app = FastAPI(
    title="新浪财经新闻插件",
    description="爬取新浪财经新闻的插件，支持根据股票代码查询相关新闻",
    version="1.0.0"
)


class NewsRequest(BaseModel):
    """新闻查询请求模型"""
    symbol: str = Field(..., description="股票代码，格式：sh600000（上海）或sz000001（深圳）")
    limit: Optional[int] = Field(5, description="返回新闻数量，默认5条", ge=1, le=20)


class NewsArticle(BaseModel):
    """新闻文章模型"""
    title: str = Field(..., description="新闻标题")
    url: str = Field(..., description="新闻链接")
    date: Optional[str] = Field(None, description="新闻日期")


class NewsResponse(BaseModel):
    """新闻响应模型"""
    symbol: str = Field(..., description="查询的股票代码")
    news_count: int = Field(..., description="返回的新闻数量")
    articles: List[NewsArticle] = Field(..., description="新闻列表")


@app.get("/", response_class=HTMLResponse)
def root():
    """根路径，返回插件信息和API文档链接"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>新浪财经新闻插件</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }
            .info {
                background: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }
            .endpoint {
                background: #e8f5e9;
                padding: 15px;
                margin: 10px 0;
                border-left: 4px solid #4CAF50;
                border-radius: 4px;
            }
            .endpoint code {
                background: #333;
                color: #4CAF50;
                padding: 2px 8px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            a {
                color: #4CAF50;
                text-decoration: none;
                font-weight: bold;
            }
            a:hover {
                text-decoration: underline;
            }
            .badge {
                display: inline-block;
                background: #4CAF50;
                color: white;
                padding: 3px 8px;
                border-radius: 3px;
                font-size: 12px;
                margin-left: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📰 新浪财经新闻插件 <span class="badge">v1.0.0</span></h1>
            
            <div class="info">
                <h3>插件说明</h3>
                <p>这是一个用于扣子（Coze）平台的新浪财经新闻爬取插件，可以根据股票代码查询相关的新浪财经新闻。</p>
            </div>

            <h2>🔗 可用端点</h2>
            
            <div class="endpoint">
                <strong>GET /</strong> - 当前页面（插件信息）
            </div>
            
            <div class="endpoint">
                <strong>GET /health</strong> - 健康检查
            </div>
            
            <div class="endpoint">
                <strong>GET /news?symbol=sh600000&limit=5</strong> - 获取新闻（GET方式）<br>
                <small>参数：symbol（股票代码，必填），limit（数量，可选，默认5）</small>
            </div>
            
            <div class="endpoint">
                <strong>POST /news</strong> - 获取新闻（POST方式）<br>
                <small>请求体：{"symbol": "sh600000", "limit": 5}</small>
            </div>

            <h2>📚 API 文档</h2>
            <p>
                <a href="/docs" target="_blank">📖 Swagger UI 文档</a> - 交互式API文档<br>
                <a href="/redoc" target="_blank">📄 ReDoc 文档</a> - 可读性更好的API文档<br>
                <a href="/openapi.json" target="_blank">🔧 OpenAPI JSON</a> - OpenAPI规范文件
            </p>

            <h2>💡 使用示例</h2>
            <div class="info">
                <p><strong>查询上海股票新闻：</strong></p>
                <code>GET /news?symbol=sh600000&limit=5</code>
                
                <p style="margin-top: 15px;"><strong>查询深圳股票新闻：</strong></p>
                <code>GET /news?symbol=sz000001&limit=10</code>
            </div>

            <h2>📝 股票代码格式</h2>
            <ul>
                <li><strong>上海股票：</strong> sh + 6位数字，例如：sh600000</li>
                <li><strong>深圳股票：</strong> sz + 6位数字，例如：sz000001</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return html_content


@app.get("/health")
def health_check():
    """健康检查端点"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/news", response_model=NewsResponse)
def get_sina_news(request: NewsRequest):
    """
    获取新浪财经新闻
    
    根据股票代码爬取新浪财经相关新闻
    """
    symbol = request.symbol.strip().lower()
    
    # 验证股票代码格式
    if not re.match(r'^(sh|sz)\d{6}$', symbol):
        raise HTTPException(
            status_code=400, 
            detail="股票代码格式错误。请使用格式：sh600000（上海）或sz000001（深圳）"
        )
    
    base_url = "https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllNewsStock.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }
    news_list = []

    try:
        # 请求新闻页面
        resp = requests.get(
            f"{base_url}?symbol={symbol}&Page=1", 
            headers=headers, 
            timeout=10
        )
        resp.raise_for_status()
        resp.encoding = 'gbk'
        
        # 解析HTML
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 查找新闻链接
        links = soup.select('div.datelist a')
        
        # 提取新闻信息
        limit = request.limit or 5
        for link in links[:limit]:
            title = link.get_text().strip()
            href = link.get('href', '')
            
            # 处理相对链接
            if href.startswith('/'):
                href = "https://vip.stock.finance.sina.com.cn" + href
            elif not href.startswith('http'):
                continue
            
            # 尝试提取日期（如果有）
            date = None
            parent = link.find_parent()
            if parent:
                date_text = parent.get_text()
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
                if date_match:
                    date = date_match.group(1)
            
            news_list.append({
                "title": title,
                "url": href,
                "date": date
            })
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500, 
            detail=f"请求失败: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"解析新闻失败: {str(e)}"
        )

    if not news_list:
        raise HTTPException(
            status_code=404,
            detail=f"未找到股票代码 {symbol} 的相关新闻"
        )

    return {
        "symbol": symbol,
        "news_count": len(news_list),
        "articles": news_list
    }


@app.get("/news", response_model=NewsResponse)
def get_sina_news_get(
    symbol: str = Query(..., description="股票代码，格式：sh600000（上海）或sz000001（深圳）"),
    limit: int = Query(5, description="返回新闻数量，默认5条", ge=1, le=20)
):
    """
    获取新浪财经新闻（GET方式）
    
    根据股票代码爬取新浪财经相关新闻
    """
    request = NewsRequest(symbol=symbol, limit=limit)
    return get_sina_news(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)