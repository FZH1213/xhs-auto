"""
Web应用 - FastAPI后端
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.storage import Database, DraftManager, DraftStatus
from src.generator import GeneratorFactory
import yaml

app = FastAPI(title="小红书自动发布系统")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
db = None
manager = None


def get_db():
    """获取数据库实例"""
    global db, manager
    if db is None:
        config = load_config()
        db = Database(config.get('database', {}).get('path', './data/drafts.db'))
        manager = DraftManager(db)
    return manager


def load_config():
    """加载配置"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'config.yaml')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


def save_config(config_data):
    """保存配置"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'config.yaml')
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)


# API模型
class GenerateRequest(BaseModel):
    topic: str
    style: str = "zhongcao"
    provider: str = "claude"
    image_count: int = 3


class UpdateDraftRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    topics: Optional[List[str]] = None


class ConfigRequest(BaseModel):
    bailian_api_key: Optional[str] = None
    bailian_model: Optional[str] = None
    claude_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None


# API路由
@app.get("/")
async def root():
    """返回主页"""
    index_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    return FileResponse(index_path)


@app.get("/api/drafts")
async def get_drafts(status: Optional[str] = None, limit: int = 50):
    """获取草稿列表"""
    manager = get_db()
    status_filter = DraftStatus(status) if status else None
    drafts = manager.get_all_drafts(status=status_filter, limit=limit)
    return {
        "success": True,
        "data": [draft.to_dict() for draft in drafts]
    }


@app.get("/api/drafts/{draft_id}")
async def get_draft(draft_id: int):
    """获取草稿详情"""
    manager = get_db()
    draft = manager.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    return {
        "success": True,
        "data": draft.to_dict()
    }


@app.post("/api/generate")
async def generate_content(request: GenerateRequest):
    """生成新内容"""
    try:
        config = load_config()

        # 检查API密钥
        if request.provider == "bailian":
            if not config.get('ai', {}).get('bailian', {}).get('api_key'):
                raise HTTPException(status_code=400, detail="未配置百炼API密钥")
        elif request.provider == "claude":
            if not config.get('ai', {}).get('claude', {}).get('api_key'):
                raise HTTPException(status_code=400, detail="未配置Claude API密钥")
        elif request.provider == "openai":
            if not config.get('ai', {}).get('openai', {}).get('api_key'):
                raise HTTPException(status_code=400, detail="未配置OpenAI API密钥")

        # 创建生成器
        text_gen = GeneratorFactory.create_text_generator(request.provider, config)
        image_gen = GeneratorFactory.create_image_generator(config)

        # 生成文本
        content_result = text_gen.generate_text(request.topic, request.style)

        # 生成图片
        image_paths = image_gen.get_images(request.topic, request.image_count)

        # 保存到数据库
        manager = get_db()
        draft = manager.create_draft(
            title=content_result['title'],
            content=content_result['content'],
            topics=content_result['topics'],
            style=request.style,
            images=image_paths
        )

        return {
            "success": True,
            "data": draft.to_dict(),
            "message": "内容生成成功"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/drafts/{draft_id}")
async def update_draft(draft_id: int, request: UpdateDraftRequest):
    """更新草稿"""
    manager = get_db()
    update_data = request.dict(exclude_unset=True)
    draft = manager.update_draft(draft_id, **update_data)

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    return {
        "success": True,
        "data": draft.to_dict(),
        "message": "更新成功"
    }


@app.put("/api/drafts/{draft_id}/approve")
async def approve_draft(draft_id: int):
    """批准草稿"""
    manager = get_db()
    draft = manager.update_status(draft_id, DraftStatus.APPROVED)

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    return {
        "success": True,
        "data": draft.to_dict(),
        "message": "已批准"
    }


@app.delete("/api/drafts/{draft_id}")
async def delete_draft(draft_id: int):
    """删除草稿"""
    manager = get_db()
    if manager.delete_draft(draft_id):
        return {
            "success": True,
            "message": "删除成功"
        }
    else:
        raise HTTPException(status_code=404, detail="草稿不存在")


@app.get("/api/config")
async def get_config():
    """获取配置"""
    config = load_config()

    # 只返回是否已配置，不返回密钥值
    bailian_key = config.get('ai', {}).get('bailian', {}).get('api_key', '')
    bailian_model = config.get('ai', {}).get('bailian', {}).get('model', 'qwen3.7-plus')
    claude_key = config.get('ai', {}).get('claude', {}).get('api_key', '')
    openai_key = config.get('ai', {}).get('openai', {}).get('api_key', '')

    return {
        "success": True,
        "data": {
            "bailian_api_key": "",  # 不返回密钥值，让用户重新输入
            "bailian_model": bailian_model,
            "claude_api_key": "",
            "openai_api_key": "",
            "has_bailian_key": bool(bailian_key),
            "has_claude_key": bool(claude_key),
            "has_openai_key": bool(openai_key),
            "image_source": config.get('image', {}).get('source', 'local_library'),
            "daily_limit": config.get('publish', {}).get('daily_limit', 3)
        }
    }


@app.post("/api/config")
async def update_config(request: ConfigRequest):
    """更新配置"""
    config = load_config()

    # 初始化结构
    if 'ai' not in config:
        config['ai'] = {}
    if 'bailian' not in config['ai']:
        config['ai']['bailian'] = {}
    if 'claude' not in config['ai']:
        config['ai']['claude'] = {}
    if 'openai' not in config['ai']:
        config['ai']['openai'] = {}

    # 更新API密钥（只更新用户输入了新值的字段）
    if request.bailian_api_key and request.bailian_api_key.strip():
        config['ai']['bailian']['api_key'] = request.bailian_api_key.strip()
    if request.bailian_model and request.bailian_model.strip():
        config['ai']['bailian']['model'] = request.bailian_model.strip()
        config['ai']['bailian']['max_tokens'] = 2000
        config['ai']['bailian']['base_url'] = 'https://coding.dashscope.aliyuncs.com/apps/anthropic'
    if request.claude_api_key and request.claude_api_key.strip():
        config['ai']['claude']['api_key'] = request.claude_api_key.strip()
    if request.openai_api_key and request.openai_api_key.strip():
        config['ai']['openai']['api_key'] = request.openai_api_key.strip()

    # 保存配置
    save_config(config)

    return {
        "success": True,
        "message": "配置已保存"
    }


@app.get("/api/styles")
async def get_styles():
    """获取可用的内容风格"""
    prompts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'prompts.yaml')
    with open(prompts_path, 'r', encoding='utf-8') as f:
        prompts = yaml.safe_load(f)

    styles = []
    for key, value in prompts.items():
        styles.append({
            "key": key,
            "name": value.get('name', key),
            "description": value.get('description', '')
        })

    return {
        "success": True,
        "data": styles
    }


@app.get("/api/stats")
async def get_stats():
    """获取统计数据"""
    manager = get_db()

    total = manager.count_drafts()
    draft_count = manager.count_drafts(DraftStatus.DRAFT)
    approved_count = manager.count_drafts(DraftStatus.APPROVED)
    published_count = manager.count_drafts(DraftStatus.PUBLISHED)

    return {
        "success": True,
        "data": {
            "total": total,
            "draft": draft_count,
            "approved": approved_count,
            "published": published_count
        }
    }


def start_web():
    """启动Web服务"""
    import uvicorn

    # 静态文件目录
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")

    print("\n" + "=" * 60)
    print("🚀 小红书自动发布系统 Web界面已启动")
    print("=" * 60)
    print(f"\n📱 访问地址: http://localhost:8000")
    print("\n💡 提示:")
    print("   - 首次使用请先在'设置'中配置API密钥")
    print("   - 按 Ctrl+C 停止服务\n")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    start_web()