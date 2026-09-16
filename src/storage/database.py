"""
数据库操作模块
"""
import os
from typing import List, Optional
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .models import Base, Draft, DraftStatus


class Database:
    """数据库管理类"""

    def __init__(self, db_path: str = "./data/drafts.db"):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        # 确保数据库目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        # 创建数据库引擎
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # 创建所有表
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class DraftManager:
    """草稿管理类"""

    def __init__(self, db: Database):
        self.db = db

    def create_draft(
        self,
        title: str,
        content: str,
        topics: List[str] = None,
        style: str = None,
        images: List[str] = None,
        meta_data: str = None
    ) -> Draft:
        """
        创建新草稿

        Args:
            title: 标题
            content: 正文内容
            topics: 话题标签列表
            style: 内容风格
            images: 图片路径列表
            meta_data: 额外元数据（JSON字符串）

        Returns:
            Draft: 创建的草稿对象
        """
        with self.db.get_session() as session:
            draft = Draft(
                title=title,
                content=content,
                topics=','.join(topics) if topics else None,
                style=style,
                images=','.join(images) if images else None,
                meta_data=meta_data
            )
            session.add(draft)
            session.flush()  # 刷新以获取ID
            session.refresh(draft)

            # 在session内访问所有属性，确保数据加载
            # 这样返回后就不会出现detached错误
            _ = draft.id
            _ = draft.title
            _ = draft.content
            _ = draft.status
            _ = draft.created_at

            # 将对象expunge，使其脱离session但仍可访问
            session.expunge(draft)
            return draft

    def get_draft(self, draft_id: int) -> Optional[Draft]:
        """
        获取指定草稿

        Args:
            draft_id: 草稿ID

        Returns:
            Draft: 草稿对象，不存在则返回None
        """
        with self.db.get_session() as session:
            draft = session.query(Draft).filter(Draft.id == draft_id).first()
            if draft:
                # 在session内访问所有属性
                session.expunge(draft)
            return draft

    def get_all_drafts(
        self,
        status: DraftStatus = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Draft]:
        """
        获取草稿列表

        Args:
            status: 状态过滤（可选）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[Draft]: 草稿列表
        """
        with self.db.get_session() as session:
            query = session.query(Draft)

            if status:
                query = query.filter(Draft.status == status)

            drafts = query.order_by(desc(Draft.created_at)).offset(offset).limit(limit).all()

            # expunge所有对象，使其脱离session但仍可访问
            for draft in drafts:
                session.expunge(draft)

            return drafts

    def update_draft(self, draft_id: int, **kwargs) -> Optional[Draft]:
        """
        更新草稿

        Args:
            draft_id: 草稿ID
            **kwargs: 要更新的字段

        Returns:
            Draft: 更新后的草稿对象
        """
        with self.db.get_session() as session:
            draft = session.query(Draft).filter(Draft.id == draft_id).first()
            if not draft:
                return None

            # 处理列表类型字段
            if 'topics' in kwargs and isinstance(kwargs['topics'], list):
                kwargs['topics'] = ','.join(kwargs['topics'])
            if 'images' in kwargs and isinstance(kwargs['images'], list):
                kwargs['images'] = ','.join(kwargs['images'])

            for key, value in kwargs.items():
                if hasattr(draft, key):
                    setattr(draft, key, value)

            session.flush()
            session.refresh(draft)

            # expunge对象，使其脱离session
            session.expunge(draft)
            return draft

    def update_status(self, draft_id: int, status: DraftStatus) -> Optional[Draft]:
        """
        更新草稿状态

        Args:
            draft_id: 草稿ID
            status: 新状态

        Returns:
            Draft: 更新后的草稿对象
        """
        return self.update_draft(draft_id, status=status)

    def delete_draft(self, draft_id: int) -> bool:
        """
        删除草稿

        Args:
            draft_id: 草稿ID

        Returns:
            bool: 是否删除成功
        """
        with self.db.get_session() as session:
            draft = session.query(Draft).filter(Draft.id == draft_id).first()
            if not draft:
                return False

            session.delete(draft)
            return True

    def count_drafts(self, status: DraftStatus = None) -> int:
        """
        统计草稿数量

        Args:
            status: 状态过滤（可选）

        Returns:
            int: 草稿数量
        """
        with self.db.get_session() as session:
            query = session.query(Draft)
            if status:
                query = query.filter(Draft.status == status)
            return query.count()