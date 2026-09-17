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
import asyncio
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.storage import Database, DraftManager, DraftStatus
from src.generator import GeneratorFactory
from src.publisher import XiaohongshuPublisher, LoginRequiredError, ValidationError
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
publisher = None
publish_records = []  # 发布记录列表
login_task = None  # 登录任务


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    print("应用启动中...")
    # 预先创建发布器实例，但不立即初始化浏览器
    config = load_config()
    global publisher
    publisher = XiaohongshuPublisher(config)
    print("✓ 发布器实例已创建")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    print("应用关闭中...")
    global publisher
    if publisher:
        await publisher.close(force=True)
        print("✓ 浏览器资源已释放")


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


def get_publisher():
    """获取发布器实例（已通过startup事件初始化）"""
    global publisher
    # publisher在应用启动时已经创建
    return publisher


async def wait_for_login_background():
    """后台等待登录任务"""
    global publisher
    try:
        if publisher and publisher.page:
            print("开始等待用户登录...")
            # 等待用户登录（最长等待5分钟）
            await publisher.login_manager.wait_for_login(publisher.page, timeout=300)
            print("✓ 登录成功！")

            # 保存登录状态
            await publisher.browser_manager.save_state()
            print("✓ 登录状态已保存")
    except Exception as e:
        print(f"✗ 登录等待出错: {str(e)}")


def get_published_today_count() -> int:
    """获取今日已发布数量"""
    today = datetime.now().date()
    return len([r for r in publish_records if r['time'].date() == today and r['success']])


def can_publish_today() -> bool:
    """检查今日是否还能发布"""
    config = load_config()
    daily_limit = config.get('publish', {}).get('daily_limit', 3)
    return get_published_today_count() < daily_limit


def get_next_available_time() -> int:
    """获取下次可发布的等待时间（秒）"""
    # 如果没有成功的发布记录，可以立即发布
    successful_records = [r for r in publish_records if r['success']]
    if not successful_records:
        return 0

    config = load_config()
    interval = config.get('publish', {}).get('interval', 300)

    last_publish = max(r['time'] for r in successful_records)
    next_time = last_publish + timedelta(seconds=interval)

    wait_seconds = (next_time - datetime.now()).total_seconds()
    return max(0, int(wait_seconds))


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


# ==================== 发布相关API ====================

@app.put("/api/drafts/{draft_id}/publish")
async def publish_draft(draft_id: int):
    """发布草稿到小红书"""
    print()
    print("=" * 60)
    print(f"开始发布草稿 #{draft_id}")
    print("=" * 60)

    try:
        manager = get_db()
        draft = manager.get_draft(draft_id)

        if not draft:
            raise HTTPException(status_code=404, detail="草稿不存在")

        print(f"✓ 找到草稿: {draft.title}")

        # 检查草稿状态
        if draft.status != DraftStatus.APPROVED:
            raise HTTPException(status_code=400, detail=f"只能发布已审核的草稿，当前状态: {draft.status.value}")

        print(f"✓ 草稿状态: {draft.status.value}")

        # 检查发布限制
        if not can_publish_today():
            raise HTTPException(status_code=429, detail="已达今日发布上限")

        print(f"✓ 发布限制检查通过")

        # 检查发布间隔
        wait_time = get_next_available_time()
        if wait_time > 0:
            raise HTTPException(
                status_code=429,
                detail=f"需等待 {wait_time} 秒后才能再次发布"
            )

        print(f"✓ 发布间隔检查通过")

        # 获取发布器
        pub = get_publisher()

        if pub.page is None:
            raise HTTPException(status_code=500, detail="浏览器未初始化，请先登录")

        print(f"✓ 浏览器已初始化")

        # 检查登录状态
        is_logged_in = await pub.check_login_status()
        if not is_logged_in:
            raise HTTPException(status_code=401, detail="未登录小红书，请先登录")

        print(f"✓ 已登录小红书")

        # 准备发布数据
        draft_data = {
            'title': draft.title,
            'content': draft.content,
            'images': draft.images.split(',') if draft.images else [],
            'topics': draft.topics.split(',') if draft.topics else []
        }

        print(f"✓ 准备发布数据:")
        print(f"  - 标题: {draft_data['title']}")
        print(f"  - 图片数: {len(draft_data['images'])}")
        print(f"  - 话题数: {len(draft_data['topics'])}")

        # 执行发布
        print()
        print("开始执行发布...")
        result = await pub.publish(draft_data)

        # 记录发布
        publish_records.append({
            'draft_id': draft_id,
            'time': datetime.now(),
            'success': result.success,
            'url': result.url
        })

        # 更新草稿状态
        if result.success:
            print()
            print("=" * 60)
            print("✓✓✓ 发布成功！")
            print("=" * 60)
            print(f"发布链接: {result.url}")

            draft = manager.update_draft(
                draft_id,
                status=DraftStatus.PUBLISHED,
                published_at=datetime.now(),
                publish_url=result.url
            )
        else:
            print()
            print("=" * 60)
            print("✗✗✗ 发布失败！")
            print("=" * 60)
            print(f"错误信息: {result.error}")

            draft = manager.update_draft(
                draft_id,
                status=DraftStatus.PUBLISH_FAILED,
                publish_error=result.error
            )

        return {
            "success": result.success,
            "data": {
                "draft_id": draft_id,
                "status": draft.status.value,
                "publish_url": result.url,
                "message": result.message or result.error
            }
        }

    except LoginRequiredError as e:
        print(f"✗ 登录失效: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except ValidationError as e:
        print(f"✗ 数据验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ 发布过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/publish/status")
async def get_publish_status():
    """获取发布状态"""
    config = load_config()

    return {
        "success": True,
        "data": {
            "daily_limit": config.get('publish', {}).get('daily_limit', 3),
            "published_today": get_published_today_count(),
            "can_publish": can_publish_today(),
            "next_available_time": get_next_available_time()
        }
    }


@app.get("/api/publish/login-status")
async def get_login_status():
    """获取登录状态"""
    try:
        pub = get_publisher()

        # 如果浏览器未初始化，返回未登录
        if pub.page is None:
            return {
                "success": True,
                "data": {
                    "logged_in": False,
                    "message": "浏览器未初始化"
                }
            }

        # 检查登录状态
        is_logged_in = await pub.check_login_status()

        # 如果已登录，尝试获取用户信息
        user_info = None
        if is_logged_in:
            try:
                # 尝试获取用户名
                user_name = await pub.page.evaluate('''
                    () => {
                        // 尝试多种方式获取用户名
                        const selectors = [
                            '.user-name',
                            '.username',
                            '[class*="userName"]',
                            '[class*="user-name"]'
                        ];
                        for (const selector of selectors) {
                            const el = document.querySelector(selector);
                            if (el && el.textContent) {
                                return el.textContent.trim();
                            }
                        }
                        return null;
                    }
                ''')

                # 尝试获取头像URL
                avatar_url = await pub.page.evaluate('''
                    () => {
                        const avatar = document.querySelector('.avatar img, .user-avatar img, [class*="avatar"] img');
                        return avatar ? avatar.src : null;
                    }
                ''')

                if user_name or avatar_url:
                    user_info = {
                        "name": user_name,
                        "avatar": avatar_url
                    }
            except Exception as e:
                print(f"获取用户信息失败: {str(e)}")

        return {
            "success": True,
            "data": {
                "logged_in": is_logged_in,
                "message": "已登录" if is_logged_in else "未登录",
                "user_info": user_info
            }
        }

    except Exception as e:
        return {
            "success": True,
            "data": {
                "logged_in": False,
                "error": str(e)
            }
        }


@app.post("/api/publish/login")
async def trigger_login():
    """触发登录流程"""
    global login_task

    try:
        pub = get_publisher()

        # 如果已经登录，直接返回
        if pub.page and await pub.check_login_status():
            return {
                "success": True,
                "message": "已经登录了"
            }

        # 初始化浏览器（如果尚未初始化）
        if pub.page is None:
            print("=" * 60)
            print("开始初始化浏览器...")
            print("=" * 60)
            try:
                await pub.init()
                print("✓ 浏览器已初始化并打开")
                print("✓ 浏览器窗口将保持打开状态")
            except Exception as init_error:
                print(f"✗ 浏览器初始化失败: {str(init_error)}")
                import traceback
                traceback.print_exc()
                raise HTTPException(
                    status_code=500,
                    detail=f"浏览器初始化失败: {str(init_error)}"
                )

        # 访问登录页面
        print("正在访问小红书创作者中心...")
        try:
            await pub.page.goto("https://creator.xiaohongshu.com", wait_until='domcontentloaded', timeout=30000)
            print("✓ 已打开小红书创作者中心")

            # 等待页面完全加载
            await asyncio.sleep(3)

            # 尝试找到并点击登录按钮
            try:
                login_btn = await pub.page.query_selector('button:has-text("登录"), a:has-text("登录")')
                if login_btn:
                    await login_btn.click()
                    print("✓ 已点击登录按钮")
                    await asyncio.sleep(2)
            except Exception:
                print("提示：如果看到登录按钮，请手动点击")
        except Exception as e:
            print(f"访问创作者中心失败: {str(e)}")

        # 启动后台登录等待任务
        if login_task is None or login_task.done():
            login_task = asyncio.create_task(wait_for_login_background())
            print("✓ 已启动登录等待后台任务")
        else:
            print("! 登录任务已在运行中")

        print("=" * 60)
        print("请在浏览器窗口中扫码登录")
        print("浏览器窗口将保持打开，请勿手动关闭")
        print("=" * 60)

        return {
            "success": True,
            "message": "请在打开的浏览器窗口中扫码登录（窗口会保持打开）",
            "browser_opened": True
        }

    except Exception as e:
        print(f"✗ 触发登录失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/publish/queue")
async def get_publish_queue():
    """获取待发布队列"""
    manager = get_db()

    # 获取所有已审核但未发布的草稿
    drafts = manager.get_all_drafts(status=DraftStatus.APPROVED)

    return {
        "success": True,
        "data": [draft.to_dict() for draft in drafts]
    }


@app.post("/api/publish/close-browser")
async def close_browser():
    """关闭浏览器窗口"""
    global publisher, login_task

    try:
        if login_task and not login_task.done():
            login_task.cancel()
            print("✓ 登录任务已取消")

        if publisher and publisher.browser_manager:
            # 强制关闭浏览器
            await publisher.browser_manager.close(force=True)
            print("✓ 浏览器已关闭")

            # 重新创建发布器实例（下次使用时会重新初始化）
            config = load_config()
            publisher = XiaohongshuPublisher(config)

        return {
            "success": True,
            "message": "浏览器已关闭"
        }

    except Exception as e:
        print(f"✗ 关闭浏览器失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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