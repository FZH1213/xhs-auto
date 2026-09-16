#!/usr/bin/env python3
"""
小红书自动发布系统 - 主程序入口
"""
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.generator import GeneratorFactory, load_config, load_prompts
from src.storage import Database, DraftManager, DraftStatus

console = Console()


@click.group()
def cli():
    """小红书自动发布系统 CLI"""
    pass


@cli.command()
@click.option('--topic', '-t', required=True, help='内容主题')
@click.option('--style', '-s', default='zhongcao', help='内容风格（zhongcao/ganhuo/diary/ceping）')
@click.option('--provider', '-p', default='claude', help='AI提供商（claude/openai）')
@click.option('--images', '-i', default=3, help='图片数量')
def generate(topic, style, provider, images):
    """生成新内容草稿"""
    try:
        console.print(f"\n[bold cyan]开始生成内容...[/bold cyan]")
        console.print(f"主题: {topic}")
        console.print(f"风格: {style}")
        console.print(f"AI: {provider}\n")

        # 加载配置
        config = load_config()
        prompts_config = load_prompts()

        # 创建生成器
        text_gen = GeneratorFactory.create_text_generator(provider, config, prompts_config)
        image_gen = GeneratorFactory.create_image_generator(config)

        # 生成文本
        console.print("[yellow]生成文本内容...[/yellow]")
        content_result = text_gen.generate_text(topic, style)

        # 生成图片
        console.print("[yellow]获取图片...[/yellow]")
        image_paths = image_gen.get_images(topic, images)

        # 保存到数据库
        db = Database(config.get('database', {}).get('path', './data/drafts.db'))
        manager = DraftManager(db)

        draft = manager.create_draft(
            title=content_result['title'],
            content=content_result['content'],
            topics=content_result['topics'],
            style=style,
            images=image_paths
        )

        # 显示结果
        console.print("\n[bold green]✓ 内容生成成功！[/bold green]\n")

        # 显示标题
        console.print(Panel(
            content_result['title'],
            title="标题",
            border_style="green"
        ))

        # 显示正文
        console.print(Panel(
            content_result['content'],
            title="正文",
            border_style="blue"
        ))

        # 显示话题
        topics_str = " ".join([f"#{t}" for t in content_result['topics']])
        console.print(f"\n[bold]话题标签:[/bold] {topics_str}")

        # 显示图片
        console.print(f"\n[bold]图片:[/bold]")
        for idx, path in enumerate(image_paths, 1):
            console.print(f"  {idx}. {path}")

        console.print(f"\n[bold]草稿ID:[/bold] {draft.id}")
        console.print(f"[bold]状态:[/bold] {draft.status.value}")

    except Exception as e:
        console.print(f"\n[bold red]✗ 错误: {str(e)}[/bold red]")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--status', '-s', default=None, help='过滤状态（draft/approved/rejected/published）')
@click.option('--limit', '-l', default=20, help='显示数量')
def list(status, limit):
    """查看草稿列表"""
    try:
        config = load_config()
        db = Database(config.get('database', {}).get('path', './data/drafts.db'))
        manager = DraftManager(db)

        # 获取状态
        status_filter = None
        if status:
            status_filter = DraftStatus(status)

        # 查询草稿
        drafts = manager.get_all_drafts(status=status_filter, limit=limit)

        if not drafts:
            console.print("\n[yellow]暂无草稿[/yellow]\n")
            return

        # 创建表格
        table = Table(title="\n草稿列表")
        table.add_column("ID", style="cyan", width=5)
        table.add_column("标题", width=30)
        table.add_column("风格", width=10)
        table.add_column("状态", width=12)
        table.add_column("创建时间", width=16)

        # 状态颜色映射
        status_colors = {
            'draft': 'yellow',
            'approved': 'green',
            'rejected': 'red',
            'published': 'blue',
            'publish_failed': 'red'
        }

        for draft in drafts:
            status_color = status_colors.get(draft.status.value, 'white')
            table.add_row(
                str(draft.id),
                draft.title[:30] + "..." if len(draft.title) > 30 else draft.title,
                draft.style or "-",
                f"[{status_color}]{draft.status.value}[/{status_color}]",
                draft.created_at.strftime("%m-%d %H:%M")
            )

        console.print(table)

        # 统计信息
        total = manager.count_drafts()
        console.print(f"\n[bold]总计: {total} 条草稿[/bold]")

    except Exception as e:
        console.print(f"\n[bold red]✗ 错误: {str(e)}[/bold red]")


@cli.command()
@click.argument('draft_id', type=int)
def view(draft_id):
    """查看草稿详情"""
    try:
        config = load_config()
        db = Database(config.get('database', {}).get('path', './data/drafts.db'))
        manager = DraftManager(db)

        draft = manager.get_draft(draft_id)

        if not draft:
            console.print(f"\n[red]草稿 #{draft_id} 不存在[/red]\n")
            return

        # 显示详情
        console.print(f"\n[bold cyan]草稿 #{draft.id}[/bold cyan]\n")

        # 标题
        console.print(Panel(
            draft.title,
            title="标题",
            border_style="green"
        ))

        # 正文
        console.print(Panel(
            draft.content,
            title="正文",
            border_style="blue"
        ))

        # 话题
        if draft.topics:
            topics = draft.topics.split(',')
            topics_str = " ".join([f"#{t}" for t in topics])
            console.print(f"\n[bold]话题标签:[/bold] {topics_str}")

        # 图片
        if draft.images:
            images = draft.images.split(',')
            console.print(f"\n[bold]图片 ({len(images)}张):[/bold]")
            for idx, path in enumerate(images, 1):
                console.print(f"  {idx}. {path}")

        # 元数据
        console.print(f"\n[bold]风格:[/bold] {draft.style or '-'}")
        console.print(f"[bold]状态:[/bold] {draft.status.value}")
        console.print(f"[bold]创建时间:[/bold] {draft.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if draft.published_at:
            console.print(f"[bold]发布时间:[/bold] {draft.published_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if draft.publish_url:
            console.print(f"[bold]发布链接:[/bold] {draft.publish_url}")

        if draft.publish_error:
            console.print(f"\n[red]发布错误: {draft.publish_error}[/red]")

        console.print()

    except Exception as e:
        console.print(f"\n[bold red]✗ 错误: {str(e)}[/bold red]")


@cli.command()
@click.argument('draft_id', type=int)
@click.option('--force', '-f', is_flag=True, help='强制删除，不确认')
def delete(draft_id, force):
    """删除草稿"""
    try:
        config = load_config()
        db = Database(config.get('database', {}).get('path', './data/drafts.db'))
        manager = DraftManager(db)

        draft = manager.get_draft(draft_id)

        if not draft:
            console.print(f"\n[red]草稿 #{draft_id} 不存在[/red]\n")
            return

        # 确认删除
        if not force:
            console.print(f"\n[yellow]即将删除草稿:[/yellow]")
            console.print(f"  ID: {draft.id}")
            console.print(f"  标题: {draft.title}")

            if not click.confirm("\n确认删除?"):
                console.print("\n[yellow]已取消[/yellow]\n")
                return

        # 删除
        if manager.delete_draft(draft_id):
            console.print(f"\n[green]✓ 草稿 #{draft_id} 已删除[/green]\n")
        else:
            console.print(f"\n[red]✗ 删除失败[/red]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ 错误: {str(e)}[/bold red]")


@cli.command()
@click.argument('draft_id', type=int)
def approve(draft_id):
    """批准草稿（标记为已审核）"""
    try:
        config = load_config()
        db = Database(config.get('database', {}).get('path', './data/drafts.db'))
        manager = DraftManager(db)

        draft = manager.update_status(draft_id, DraftStatus.APPROVED)

        if draft:
            console.print(f"\n[green]✓ 草稿 #{draft_id} 已标记为已审核[/green]\n")
        else:
            console.print(f"\n[red]✗ 草稿不存在[/red]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ 错误: {str(e)}[/bold red]")


@cli.command()
def web():
    """启动Web审核界面"""
    try:
        console.print("\n[bold cyan]启动Web审核界面...[/bold cyan]")
        console.print("[yellow]访问: http://localhost:8000[/yellow]\n")

        # 导入Web应用
        from src.web.app import start_web
        start_web()

    except ImportError:
        console.print("\n[yellow]Web模块尚未实现[/yellow]")
        console.print("[yellow]提示: 运行 'python main.py --help' 查看可用命令[/yellow]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ 错误: {str(e)}[/bold red]")


@cli.command()
def config():
    """查看当前配置"""
    try:
        conf = load_config()
        prompts = load_prompts()

        console.print("\n[bold cyan]系统配置[/bold cyan]\n")

        # AI配置
        console.print("[bold]AI提供商:[/bold]")
        if conf.get('ai', {}).get('claude', {}).get('api_key'):
            console.print("  ✓ Claude 已配置")
        if conf.get('ai', {}).get('openai', {}).get('api_key'):
            console.print("  ✓ OpenAI 已配置")

        # 图片配置
        console.print(f"\n[bold]图片来源:[/bold] {conf.get('image', {}).get('source')}")
        console.print(f"[bold]素材库路径:[/bold] {conf.get('image', {}).get('local_library_path')}")

        # 数据库配置
        console.print(f"\n[bold]数据库路径:[/bold] {conf.get('database', {}).get('path')}")

        # 可用风格
        console.print(f"\n[bold]可用内容风格:[/bold]")
        for style, info in prompts.items():
            console.print(f"  • {style}: {info.get('name', style)}")

        console.print()

    except Exception as e:
        console.print(f"\n[bold red]✗ 错误: {str(e)}[/bold red]")


if __name__ == '__main__':
    cli()