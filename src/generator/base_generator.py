"""
内容生成器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
import yaml
import os


class ContentGenerator(ABC):
    """内容生成器基类"""

    def __init__(self, config: Dict, prompts_config: Dict):
        """
        初始化生成器

        Args:
            config: 系统配置
            prompts_config: 提示词模板配置
        """
        self.config = config
        self.prompts_config = prompts_config

    @abstractmethod
    def generate_text(self, topic: str, style: str = "zhongcao") -> Dict[str, str]:
        """
        生成文本内容

        Args:
            topic: 主题
            style: 内容风格

        Returns:
            Dict: 包含title, content, topics的字典
        """
        pass

    def load_prompt_template(self, style: str) -> Optional[Dict]:
        """
        加载提示词模板

        Args:
            style: 风格名称

        Returns:
            Dict: 提示词模板
        """
        return self.prompts_config.get(style)

    def parse_generated_content(self, text: str) -> Dict[str, str]:
        """
        解析AI生成的内容

        Args:
            text: AI生成的原始文本

        Returns:
            Dict: 包含title, content, topics的字典
        """
        result = {
            'title': '',
            'content': '',
            'topics': []
        }

        lines = text.strip().split('\n')

        # 尝试解析标题
        for i, line in enumerate(lines):
            if '标题' in line or '题目' in line:
                # 提取标题内容
                if '：' in line:
                    result['title'] = line.split('：', 1)[1].strip()
                elif ':' in line:
                    result['title'] = line.split(':', 1)[1].strip()
                elif i + 1 < len(lines):
                    result['title'] = lines[i + 1].strip()
                break

        # 尝试解析正文
        content_start = False
        content_lines = []

        for line in lines:
            if '正文' in line or '内容' in line:
                content_start = True
                continue
            if '话题' in line or '标签' in line:
                # 提取话题
                if '：' in line:
                    topics_str = line.split('：', 1)[1]
                elif ':' in line:
                    topics_str = line.split(':', 1)[1]
                else:
                    continue

                # 提取话题标签
                import re
                topics = re.findall(r'#([^#\s]+)', topics_str)
                result['topics'] = topics
                break

            if content_start:
                content_lines.append(line)

        result['content'] = '\n'.join(content_lines).strip()

        # 如果解析失败，尝试更简单的方式
        if not result['title'] or not result['content']:
            # 第一行作为标题
            if not result['title'] and lines:
                result['title'] = lines[0].strip()

            # 其余作为内容
            if not result['content'] and len(lines) > 1:
                result['content'] = '\n'.join(lines[1:]).strip()

        return result


def load_config(config_path: str = "./config/config.yaml") -> Dict:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        Dict: 配置字典
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_prompts(prompts_path: str = "./config/prompts.yaml") -> Dict:
    """
    加载提示词模板

    Args:
        prompts_path: 提示词模板路径

    Returns:
        Dict: 提示词模板字典
    """
    with open(prompts_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)