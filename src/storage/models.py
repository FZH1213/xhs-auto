"""
数据模型定义
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum

Base = declarative_base()


class DraftStatus(PyEnum):
    """草稿状态枚举"""
    DRAFT = "draft"              # 草稿（待审核）
    APPROVED = "approved"        # 已审核通过
    REJECTED = "rejected"        # 已拒绝
    PUBLISHED = "published"      # 已发布
    PUBLISH_FAILED = "publish_failed"  # 发布失败


class Draft(Base):
    """草稿数据模型"""
    __tablename__ = 'drafts'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 内容字段
    title = Column(String(100), nullable=False, comment='标题')
    content = Column(Text, nullable=False, comment='正文内容')
    topics = Column(String(500), comment='话题标签，逗号分隔')
    style = Column(String(50), comment='内容风格')

    # 图片字段
    images = Column(String(1000), comment='图片路径，逗号分隔')

    # 状态字段
    status = Column(
        Enum(DraftStatus),
        default=DraftStatus.DRAFT,
        comment='草稿状态'
    )

    # 时间字段
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment='更新时间'
    )
    published_at = Column(DateTime, comment='发布时间')

    # 发布信息
    publish_url = Column(String(500), comment='发布后的链接')
    publish_error = Column(Text, comment='发布错误信息')

    # 元数据
    meta_data = Column(Text, comment='额外元数据（JSON格式）')

    def __repr__(self):
        return f"<Draft(id={self.id}, title='{self.title}', status={self.status.value})>"

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'topics': self.topics.split(',') if self.topics else [],
            'style': self.style,
            'images': self.images.split(',') if self.images else [],
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'publish_url': self.publish_url,
            'publish_error': self.publish_error,
        }