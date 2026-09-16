"""
Claude AI 内容生成器
"""
from typing import Dict
import anthropic
from .base_generator import ContentGenerator


class ClaudeGenerator(ContentGenerator):
    """Claude AI 生成器"""

    def __init__(self, config: Dict, prompts_config: Dict):
        super().__init__(config, prompts_config)

        # 初始化Claude客户端
        claude_config = config.get('ai', {}).get('claude', {})
        self.client = anthropic.Anthropic(
            api_key=claude_config.get('api_key')
        )
        self.model = claude_config.get('model', 'claude-sonnet-4-6')
        self.max_tokens = claude_config.get('max_tokens', 2000)

    def generate_text(self, topic: str, style: str = "zhongcao") -> Dict[str, str]:
        """
        使用Claude生成文本内容

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

        # 调用Claude API
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        # 获取生成的内容
        generated_text = message.content[0].text

        # 解析内容
        result = self.parse_generated_content(generated_text)

        return result