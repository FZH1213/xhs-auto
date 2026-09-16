"""
阿里云百炼平台生成器 - Anthropic API格式（支持GLM-5）
"""
from typing import Dict
import anthropic
from .base_generator import ContentGenerator


class BailianGenerator(ContentGenerator):
    """阿里云百炼平台生成器 - Anthropic API格式"""

    def __init__(self, config: Dict, prompts_config: Dict):
        super().__init__(config, prompts_config)

        # 初始化百炼客户端（使用Anthropic API格式）
        bailian_config = config.get('ai', {}).get('bailian', {})
        self.client = anthropic.Anthropic(
            api_key=bailian_config.get('api_key'),
            base_url=bailian_config.get('base_url', 'https://coding.dashscope.aliyuncs.com/apps/anthropic')
        )
        self.model = bailian_config.get('model', 'glm-5')
        self.max_tokens = bailian_config.get('max_tokens', 2000)

    def generate_text(self, topic: str, style: str = "zhongcao") -> Dict[str, str]:
        """
        使用百炼平台生成文本内容

        Args:
            topic: 主题
            style: 内容风格

        Returns:
            Dict: 包含title, content, topics的字典
        """
        # 加载提示词模板
        template = self.load_prompt_template(style)
        if not template:
            raise ValueError(f"未找到风格模板: {style}")

        system_prompt = template['system_prompt']
        user_prompt = template['user_prompt'].replace('{{topic}}', topic)

        # 调用百炼API（Anthropic格式）
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        # 处理响应内容（GLM-5可能返回ThinkingBlock和TextBlock）
        text_parts = []
        for block in message.content:
            # 检查是否是文本块（type='text'）
            if hasattr(block, 'type') and block.type == 'text':
                if hasattr(block, 'text'):
                    text_parts.append(block.text)

        # 合并所有文本
        generated_text = '\n'.join(text_parts)

        if not generated_text:
            raise ValueError("API返回的内容为空，请检查模型配置")

        # 解析内容
        result = self.parse_generated_content(generated_text)

        return result