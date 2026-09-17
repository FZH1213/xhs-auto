#!/usr/bin/env python3
"""
浏览器启动诊断脚本
用于排查浏览器闪退问题
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


async def diagnose_browser():
    """诊断浏览器启动问题"""
    print("=" * 60)
    print("浏览器启动诊断")
    print("=" * 60)
    print()

    try:
        # 加载配置
        config = load_config()
        print(f"✓ 配置加载成功")
        print(f"  - headless: {config.get('browser', {}).get('headless', False)}")
        print(f"  - storage_path: {config.get('browser', {}).get('storage_path', './data/browser_state')}")

        # 创建浏览器管理器
        browser_manager = BrowserManager(config)
        print(f"✓ 浏览器管理器创建成功")

        # 初始化浏览器
        print()
        print("开始初始化浏览器...")
        print()
        page = await browser_manager.init_browser()
        print()
        print("✓ 浏览器初始化成功")

        # 访问测试页面
        print()
        print("正在访问测试页面...")
        await page.goto("https://www.baidu.com", timeout=30000)
        print("✓ 页面访问成功")

        print()
        print("=" * 60)
        print("✓✓✓ 诊断成功！浏览器窗口应该保持打开")
        print("=" * 60)
        print()
        print("浏览器窗口将在10秒后保持打开...")
        print("如果窗口保持打开，说明浏览器管理器工作正常")
        print("如果窗口关闭，说明有其他问题")
        print()

        # 保持运行一段时间
        await asyncio.sleep(10)

        print()
        print("✓ 浏览器窗口仍然打开！")
        print()
        print("按 Ctrl+C 可以退出，浏览器窗口会保持打开")
        print("或者关闭此终端窗口")

        # 无限等待
        try:
            await asyncio.sleep(999999)
        except KeyboardInterrupt:
            print("\n退出诊断")

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
        print()
        print("提示：浏览器窗口应该保持打开，请查看窗口状态")
        input("按Enter键退出...")


if __name__ == "__main__":
    print()
    print("说明：")
    print("- 此脚本会打开一个浏览器窗口")
    print("- 窗口应该保持打开，不会自动关闭")
    print("- 如果窗口自动关闭，说明有问题")
    print()
    input("按Enter键继续...")

    asyncio.run(diagnose_browser())