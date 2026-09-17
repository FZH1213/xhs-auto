#!/usr/bin/env python3
"""
自动诊断脚本（不需要用户输入）
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.publisher.browser_manager import BrowserManager
import yaml


def load_config():
    """加载配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


async def auto_diagnose():
    """自动诊断"""
    print("=" * 60)
    print("自动诊断 - 浏览器管理器")
    print("=" * 60)
    print()

    try:
        # 加载配置
        config = load_config()
        print(f"✓ 配置加载成功")

        # 创建浏览器管理器
        browser_manager = BrowserManager(config)
        print(f"✓ 浏览器管理器创建成功")

        # 初始化浏览器
        print()
        print("开始初始化浏览器...")
        page = await browser_manager.init_browser()

        print()
        print("=" * 60)
        print("✓✓✓ 浏览器初始化成功！")
        print("=" * 60)
        print()

        # 访问测试页面
        print("正在访问百度测试页面...")
        await page.goto("https://www.baidu.com", timeout=30000)
        print("✓ 页面访问成功")

        print()
        print("=" * 60)
        print("✓✓✓ 所有测试通过！")
        print("=" * 60)
        print()
        print("浏览器窗口将保持打开15秒...")

        await asyncio.sleep(15)

        print()
        print("测试完成！浏览器工作正常。")
        print()

        # 清理
        await browser_manager.close(force=True)

    except Exception as e:
        print()
        print("=" * 60)
        print("✗✗✗ 诊断失败")
        print("=" * 60)
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print()
        print("详细错误堆栈:")
        import traceback
        traceback.print_exc()
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(auto_diagnose())