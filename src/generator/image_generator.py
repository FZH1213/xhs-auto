"""
图片生成/处理模块
"""
from typing import List, Optional, Dict
import os
import random
from PIL import Image
import requests
from io import BytesIO


class ImageGenerator:
    """图片生成器"""

    def __init__(self, config: Dict):
        """
        初始化图片生成器

        Args:
            config: 配置字典
        """
        self.config = config
        image_config = config.get('image', {})
        self.source = image_config.get('source', 'local_library')
        self.library_path = image_config.get('local_library_path', './data/images')

        # 确保图片目录存在
        os.makedirs(self.library_path, exist_ok=True)

    def get_images(self, topic: str, count: int = 3) -> List[str]:
        """
        获取图片

        Args:
            topic: 主题
            count: 需要的图片数量

        Returns:
            List[str]: 图片路径列表
        """
        if self.source == 'local_library':
            return self._get_from_library(count)
        elif self.source == 'unsplash':
            return self._get_from_unsplash(topic, count)
        else:
            raise ValueError(f"不支持的图片来源: {self.source}")

    def _get_from_library(self, count: int) -> List[str]:
        """
        从本地素材库获取图片

        Args:
            count: 需要的图片数量

        Returns:
            List[str]: 图片路径列表
        """
        # 获取所有图片文件
        image_files = []
        for root, dirs, files in os.walk(self.library_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    image_files.append(os.path.join(root, file))

        if not image_files:
            # 如果没有图片，创建占位图
            print(f"⚠️ 素材库为空，创建占位图...")
            return self._create_placeholder_images(count)

        # 随机选择图片
        selected = random.sample(image_files, min(count, len(image_files)))

        # 如果不够，复制已有的图片
        while len(selected) < count:
            selected.append(random.choice(image_files))

        return selected

    def _get_from_unsplash(self, topic: str, count: int) -> List[str]:
        """
        从Unsplash获取图片

        Args:
            topic: 搜索关键词
            count: 需要的图片数量

        Returns:
            List[str]: 图片路径列表
        """
        # 注意：实际使用需要Unsplash API key
        # 这里只是一个示例实现
        print(f"⚠️ Unsplash API需要配置API key")
        return self._create_placeholder_images(count)

    def _create_placeholder_images(self, count: int) -> List[str]:
        """
        创建占位图

        Args:
            count: 需要的图片数量

        Returns:
            List[str]: 占位图路径列表
        """
        from PIL import Image, ImageDraw, ImageFont

        paths = []
        colors = [
            (255, 182, 193),  # 浅粉
            (173, 216, 230),  # 浅蓝
            (144, 238, 144),  # 浅绿
            (255, 218, 185),  # 浅橙
            (221, 160, 221),  # 浅紫
        ]

        for i in range(count):
            # 创建图片
            img = Image.new('RGB', (1080, 1080), colors[i % len(colors)])
            draw = ImageDraw.Draw(img)

            # 添加文字
            text = f"图片 {i+1}"

            # 尝试加载字体，如果失败则使用默认字体
            try:
                font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 60)
            except:
                font = ImageFont.load_default()

            # 计算文字位置（居中）
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            position = ((1080 - text_width) // 2, (1080 - text_height) // 2)

            # 绘制文字
            draw.text(position, text, fill=(100, 100, 100), font=font)

            # 保存图片
            filename = f"placeholder_{i+1}.png"
            filepath = os.path.join(self.library_path, filename)
            img.save(filepath)
            paths.append(filepath)

        return paths

    def resize_image(self, image_path: str, size: tuple = (1080, 1080)) -> str:
        """
        调整图片大小

        Args:
            image_path: 图片路径
            size: 目标大小

        Returns:
            str: 调整后的图片路径
        """
        with Image.open(image_path) as img:
            # 创建新图片
            new_img = Image.new('RGB', size, (255, 255, 255))

            # 调整大小并保持比例
            img.thumbnail(size)
            width, height = img.size

            # 居中粘贴
            x = (size[0] - width) // 2
            y = (size[1] - height) // 2
            new_img.paste(img, (x, y))

            # 保存
            filename = f"resized_{os.path.basename(image_path)}"
            new_path = os.path.join(self.library_path, filename)
            new_img.save(new_path)

            return new_path