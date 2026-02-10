"""
数据库模型 - 使用 peewee + SQLite
数据库文件保存在项目根目录 data/toutiao.db
"""

import os
import threading
from datetime import datetime
from peewee import (
    SqliteDatabase, Model, CharField, TextField, IntegerField,
    BooleanField, DateTimeField, BigIntegerField,
)
from logger import get_logger

log = get_logger('db')

# 数据库路径
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'toutiao.db')

db = SqliteDatabase(DB_PATH, pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 64,
    'foreign_keys': 1,
    'busy_timeout': 30000,  # 等待锁最多 30 秒
})

# 写操作锁，保证多线程写入串行
_write_lock = threading.Lock()


class BaseModel(Model):
    class Meta:
        database = db


class Account(BaseModel):
    """对标账号表"""
    url = CharField(unique=True, index=True, help_text='账号链接')
    category = CharField(default='', index=True, help_text='类型/分类')
    created_at = DateTimeField(default=datetime.now, help_text='添加时间')

    class Meta:
        table_name = 'accounts'
        order_by = ['-created_at']

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'category': self.category,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
        }


class Setting(BaseModel):
    """设置表（key-value）"""
    key = CharField(unique=True, index=True, help_text='设置键')
    value = TextField(default='', help_text='设置值(JSON)')

    class Meta:
        table_name = 'settings'

    @staticmethod
    def get_val(key, default=None):
        """获取设置值"""
        try:
            db.connect(reuse_if_open=True)
            row = Setting.get_or_none(Setting.key == key)
            if row:
                import json
                return json.loads(row.value)
        except Exception:
            pass
        return default

    @staticmethod
    def set_val(key, value):
        """设置值"""
        import json
        db.connect(reuse_if_open=True)
        with _write_lock:
            Setting.insert(key=key, value=json.dumps(value, ensure_ascii=False)).on_conflict(
                conflict_target=[Setting.key],
                update={Setting.value: json.dumps(value, ensure_ascii=False)},
            ).execute()

    @staticmethod
    def get_all(defaults=None):
        """获取所有设置，合并默认值"""
        result = dict(defaults) if defaults else {}
        try:
            db.connect(reuse_if_open=True)
            import json
            for row in Setting.select():
                try:
                    result[row.key] = json.loads(row.value)
                except Exception:
                    result[row.key] = row.value
        except Exception:
            pass
        return result

    @staticmethod
    def save_all(data):
        """批量保存设置"""
        import json
        db.connect(reuse_if_open=True)
        with _write_lock, db.atomic():
            for k, v in data.items():
                Setting.insert(key=k, value=json.dumps(v, ensure_ascii=False)).on_conflict(
                    conflict_target=[Setting.key],
                    update={Setting.value: json.dumps(v, ensure_ascii=False)},
                ).execute()


class Article(BaseModel):
    """文章表"""
    group_id = CharField(unique=True, index=True, help_text='文章ID')
    category = CharField(default='', index=True, help_text='分类')
    title = CharField(default='', help_text='标题')
    abstract = TextField(default='', help_text='摘要')
    url = CharField(default='', help_text='文章链接')
    share_url = CharField(default='', help_text='分享链接')
    source = CharField(default='', help_text='来源/作者名')
    content_type = CharField(default='text', help_text='内容类型: video/image/text')

    publish_time = IntegerField(default=0, help_text='发布时间戳')
    publish_time_str = CharField(default='', help_text='发布时间可读')

    read_count = IntegerField(default=0, help_text='阅读数')
    show_count = IntegerField(default=0, help_text='展示数')
    like_count = IntegerField(default=0, help_text='点赞数')
    comment_count = IntegerField(default=0, help_text='评论数')
    share_count = IntegerField(default=0, help_text='分享数')
    repin_count = IntegerField(default=0, help_text='收藏数')
    video_watch_count = IntegerField(default=0, help_text='视频播放数')
    image_count = IntegerField(default=0, help_text='图片数')

    user_name = CharField(default='', help_text='作者名')
    user_avatar = CharField(default='', help_text='作者头像')
    user_id = CharField(default='', index=True, help_text='作者ID')

    is_rewritten = BooleanField(default=False, index=True, help_text='是否已改写')
    doc_path = CharField(default='', help_text='文档路径')

    created_at = DateTimeField(default=datetime.now, help_text='入库时间')
    updated_at = DateTimeField(default=datetime.now, help_text='更新时间')

    class Meta:
        table_name = 'articles'
        order_by = ['-publish_time']

    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'category': self.category,
            'title': self.title,
            'abstract': self.abstract,
            'url': self.url,
            'share_url': self.share_url,
            'source': self.source,
            'content_type': self.content_type,
            'publish_time': self.publish_time,
            'publish_time_str': self.publish_time_str,
            'read_count': self.read_count,
            'show_count': self.show_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'share_count': self.share_count,
            'repin_count': self.repin_count,
            'video_watch_count': self.video_watch_count,
            'image_count': self.image_count,
            'user_name': self.user_name,
            'user_avatar': self.user_avatar,
            'user_id': self.user_id,
            'is_rewritten': self.is_rewritten,
            'doc_path': self.doc_path,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
        }


def init_db():
    """初始化数据库，创建表"""
    db.connect(reuse_if_open=True)
    db.create_tables([Account, Setting, Article], safe=True)
    log.info(f'数据库初始化完成: {DB_PATH}')


def save_articles(article_dicts, category=''):
    """
    批量保存文章到数据库，已存在的更新计数数据，新的插入
    线程安全：通过 _write_lock 保证串行写入
    返回 (新增数, 更新数)
    """
    inserted = 0
    updated = 0
    now = datetime.now()

    with _write_lock, db.atomic():
        for data in article_dicts:
            gid = data.get('group_id', '')
            if not gid:
                continue

            existing = Article.get_or_none(Article.group_id == gid)
            if existing:
                # 更新计数字段
                Article.update(
                    read_count=data.get('read_count', 0),
                    show_count=data.get('show_count', 0),
                    like_count=data.get('like_count', 0),
                    comment_count=data.get('comment_count', 0),
                    share_count=data.get('share_count', 0),
                    repin_count=data.get('repin_count', 0),
                    video_watch_count=data.get('video_watch_count', 0),
                    updated_at=now,
                ).where(Article.group_id == gid).execute()
                updated += 1
            else:
                Article.create(
                    group_id=gid,
                    category=category,
                    title=data.get('title', ''),
                    abstract=data.get('abstract', ''),
                    url=data.get('url', ''),
                    share_url=data.get('share_url', ''),
                    source=data.get('source', ''),
                    content_type=data.get('content_type', 'text'),
                    publish_time=data.get('publish_time', 0),
                    publish_time_str=data.get('publish_time_str', ''),
                    read_count=data.get('read_count', 0),
                    show_count=data.get('show_count', 0),
                    like_count=data.get('like_count', 0),
                    comment_count=data.get('comment_count', 0),
                    share_count=data.get('share_count', 0),
                    repin_count=data.get('repin_count', 0),
                    video_watch_count=data.get('video_watch_count', 0),
                    image_count=data.get('image_count', 0),
                    user_name=data.get('user_name', ''),
                    user_avatar=data.get('user_avatar', ''),
                    user_id=data.get('user_id', ''),
                    is_rewritten=False,
                    created_at=now,
                    updated_at=now,
                )
                inserted += 1

    log.info(f'文章入库: 新增 {inserted}, 更新 {updated}')
    return inserted, updated
