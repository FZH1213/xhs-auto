"""
内容生成器工厂
"""
from typing import Dict, Optional
from .base_generator import ContentGenerator, load_config, load_prompts
from .claude_generator import ClaudeGenerator
from .openai_generator import OpenAIGenerator
from .bailian_generator import BailianGenerator
from .image_generator import ImageGenerator


class GeneratorFactory:
    """内容生成器工厂"""

    @staticmethod
    def create_text_generator(
        provider: str = "bailian",
        config: Dict = None,
        prompts_config: Dict = None
    ) -> ContentGenerator:
        """
        创建文本生成器

        Args:
            provider: AI提供商（bailian/claude/openai）
            config: 配置字典
            prompts_config: 提示词配置

        Returns:
            ContentGenerator: 生成器实例
        """
        if config is None:
            config = load_config()

        if prompts_config is None:
            prompts_config = load_prompts()

        if provider == "bailian":
            return BailianGenerator(config, prompts_config)
        elif provider == "claude":
            return ClaudeGenerator(config, prompts_config)
        elif provider == "openai":
            return OpenAIGenerator(config, prompts_config)
        else:
            raise ValueError(f"不支持的AI提供商: {provider}")

    @staticmethod
    def create_image_generator(config: Dict = None) -> ImageGenerator:
        """
        创建图片生成器

        Args:
            config: 配置字典

        Returns:
            ImageGenerator: 图片生成器实例
        """
        if config is None:
            config = load_config()

        return ImageGenerator(config)