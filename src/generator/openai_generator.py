"""
OpenAI 内容生成器
"""
from typing import Dict
from openai import OpenAI
from .base_generator import ContentGenerator


class OpenAIGenerator(ContentGenerator):
    """OpenAI 生成器"""

    def __init__(self, config: Dict, prompts_config: Dict):
        super().__init__(config, prompts_config)

        # 初始化OpenAI客户端
        openai_config = config.get('ai', {}).get('openai', {})
        self.client = OpenAI(
            api_key=openai_config.get('api_key')
        )
        self.model = openai_config.get('model', 'gpt-4')
        self.max_tokens = openai_config.get('max_tokens', 2000)

    def generate_text(self, topic: str, style: str = "zhongcao") -> Dict[str, str]:
        """
        使用OpenAI生成文本内容

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

        # 调用OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        # 获取生成的内容
        generated_text = response.choices[0].message.content

        # 解析内容
        result = self.parse_generated_content(generated_text)

        return result