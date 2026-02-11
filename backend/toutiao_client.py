"""
ToutiaoClient - 头条对标账号数据采集客户端
使用 Playwright 打开账号主页，监听 feed 接口，解析文章数据
"""

import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from logger import get_logger
from fingerprint import random_fingerprint

log = get_logger('collector')


# 目标 API 地址
FEED_API_URL = 'https://www.toutiao.com/api/pc/list/feed'


class ArticleItem:
    """解析后的文章数据"""

    def __init__(self, raw: dict):
        self.raw = raw
        self.group_id = raw.get('group_id', '') or raw.get('item_id', '')
        self.title = raw.get('title', '')
        self.abstract = raw.get('abstract', '')
        self.url = raw.get('article_url', '') or raw.get('url', '')
        self.share_url = raw.get('share_url', '')
        self.source = raw.get('source', '')
        self.publish_time = raw.get('publish_time', 0)
        self.has_video = raw.get('has_video', False)
        self.has_image = raw.get('has_image', False)

        # 基础计数
        self.read_count = raw.get('read_count', 0)
        self.like_count = raw.get('like_count', 0)
        self.comment_count = raw.get('comment_count', 0)
        self.repin_count = raw.get('repin_count', 0)

        # 详细计数 (来自 itemCell.itemCounter)
        item_cell = raw.get('itemCell', {})
        counter = item_cell.get('itemCounter', {})
        self.show_count = counter.get('showCount', 0)
        self.share_count = counter.get('shareCount', 0)
        self.digg_count = counter.get('diggCount', self.like_count)
        self.detail_read_count = counter.get('readCount', self.read_count)
        self.detail_comment_count = counter.get('commentCount', self.comment_count)
        self.detail_repin_count = counter.get('repinCount', self.repin_count)
        self.video_watch_count = counter.get('videoWatchCount', 0)

        # 用户信息
        user_info = raw.get('user_info', {})
        self.user_name = user_info.get('name', '')
        self.user_avatar = user_info.get('avatar_url', '')
        self.user_id = user_info.get('user_id', '')
        self.user_verified = user_info.get('user_verified', False)
        self.verified_content = user_info.get('verified_content', '')

        # 图片
        image_list = raw.get('image_list', [])
        self.image_count = len(image_list)
        self.images = [img.get('url', '') for img in image_list if img.get('url')]

    @property
    def publish_time_str(self):
        """发布时间的可读格式"""
        if self.publish_time:
            return datetime.fromtimestamp(self.publish_time).strftime('%Y-%m-%d %H:%M:%S')
        return ''

    @property
    def content_type(self):
        """内容类型"""
        if self.has_video:
            return 'video'
        if self.has_image:
            return 'image'
        return 'text'

    def to_dict(self):
        """转为字典，用于前端展示或存储"""
        return {
            'group_id': str(self.group_id),
            'title': self.title,
            'abstract': self.abstract,
            'url': self.url,
            'share_url': self.share_url,
            'source': self.source,
            'content_type': self.content_type,
            'publish_time': self.publish_time,
            'publish_time_str': self.publish_time_str,
            'read_count': self.detail_read_count,
            'show_count': self.show_count,
            'like_count': self.digg_count,
            'comment_count': self.detail_comment_count,
            'share_count': self.share_count,
            'repin_count': self.detail_repin_count,
            'video_watch_count': self.video_watch_count,
            'image_count': self.image_count,
            'user_name': self.user_name,
            'user_avatar': self.user_avatar,
            'user_id': self.user_id,
        }

    def __repr__(self):
        return f'<Article "{self.title[:30]}" reads={self.detail_read_count} likes={self.digg_count}>'


class ToutiaoClient:
    """
    头条数据采集客户端
    打开用户主页，通过网络拦截获取 feed 接口数据
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._articles = []       # 采集到的文章列表
        self._has_more = True      # 是否还有更多数据
        self._feed_responses = []  # 原始 feed 响应缓存
        self._collecting = False
        self._on_progress = None   # 进度回调 (message, articles_count)
        self._since_time = 0       # 时间过滤：只采集此时间戳之后的文章

    @property
    def is_running(self):
        return self._browser is not None

    @property
    def articles(self):
        return self._articles

    async def launch(self, headless=False):
        """启动浏览器（普通模式，不指定 user_data_dir）"""
        log.info(f'启动采集浏览器 (headless={headless})')
        if self._context:
            await self.close()

        self._playwright = await async_playwright().start()
        fp = random_fingerprint()
        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-infobars',
                '--disable-extensions',
            ],
        )
        self._context = await self._browser.new_context(
            viewport=fp['viewport'],
            user_agent=fp['user_agent'],
            locale=fp['locale'],
            timezone_id=fp['timezone_id'],
            color_scheme=fp['color_scheme'],
            device_scale_factor=fp['device_scale_factor'],
            extra_http_headers=fp['extra_http_headers'],
        )
        self._page = await self._context.new_page()
        log.info('采集浏览器启动完成')

    async def close(self):
        """关闭浏览器"""
        log.info('关闭采集浏览器')
        self._collecting = False
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

    async def collect_account(self, account_url, on_progress=None, since_time=0, timeout=60, **_kwargs):
        """
        采集单个账号的文章数据
        打开页面，拦截到 feed 接口数据后立即解析、过滤，然后关闭浏览器返回。

        Args:
            account_url: 账号主页链接
            on_progress: 进度回调 (message: str, count: int)
            since_time: Unix 时间戳，只采集该时间点之后发布的文章，0 表示不过滤
            timeout: 采集超时时间（秒），默认 60 秒

        Returns:
            list[dict]: 解析后的文章列表
        """
        if not self._page:
            raise RuntimeError('浏览器未启动，请先调用 launch()')

        self._articles = []
        self._feed_responses = []
        self._collecting = True
        self._on_progress = on_progress
        self._since_time = since_time

        # 使用当前运行中的事件循环创建 future
        loop = asyncio.get_running_loop()
        self._feed_received = loop.create_future()

        since_str = datetime.fromtimestamp(since_time).strftime('%Y-%m-%d %H:%M:%S') if since_time else '不限'
        log.info(f'开始采集: {account_url}')
        log.info(f'参数: since={since_str}, timeout={timeout}s')

        # 页面加载超时 = 采集超时的一半，至少 15 秒
        page_timeout = max(int(timeout * 1000 // 2), 15000)
        # Feed 等待超时 = 采集超时减去页面加载预留，至少 10 秒
        feed_timeout = max(timeout - page_timeout // 1000 - 5, 10)

        # 注册网络响应监听（必须在 goto 之前注册）
        self._page.on('response', self._on_response)

        try:
            self._notify('正在打开账号页面...', 0)
            # 使用 load 等待 JS 执行完毕，确保 feed API 被触发
            await self._page.goto(account_url, wait_until='load', timeout=page_timeout)

            self._notify('等待 Feed 数据...', 0)

            # 等待拦截到 feed 数据
            try:
                await asyncio.wait_for(asyncio.shield(self._feed_received), timeout=feed_timeout)
            except asyncio.TimeoutError:
                # 超时后再等一小段，有时 feed 请求稍晚才发出
                log.warning('首次等待超时，额外等待 5 秒...')
                await self._page.wait_for_timeout(5000)

            current_url = self._page.url
            log.debug(f'当前页面URL: {current_url}')
            self._notify(f'采集完成，共 {len(self._articles)} 篇文章', len(self._articles))

        finally:
            self._page.remove_listener('response', self._on_response)
            self._collecting = False

        # 拦截到数据后关闭浏览器
        log.info(f'数据已获取，关闭浏览器。共 {len(self._articles)} 篇')
        await self.close()

        return [a.to_dict() for a in self._articles]

    async def _on_response(self, response):
        """监听网络响应，拦截 feed 接口，拿到数据后立即解析并通知完成"""
        try:
            url = response.url
            if FEED_API_URL not in url:
                return

            log.info(f'拦截到 Feed 请求: status={response.status}, url={url[:100]}')

            if response.status != 200:
                log.warning(f'Feed 接口非 200 响应: status={response.status}')
                return

            body = await response.json()
            data_list = body.get('data', [])
            data_count = len(data_list) if isinstance(data_list, list) else 0
            log.info(f'Feed 响应解析成功: {data_count} 条数据, has_more={body.get("has_more")}')
            self._feed_responses.append(body)
            self._parse_feed_response(body)

            # 通知 collect_account 数据已到达
            if self._feed_received and not self._feed_received.done():
                self._feed_received.set_result(True)

        except Exception as e:
            log.warning(f'解析 Feed 响应异常: {e}')

    def _parse_feed_response(self, body):
        """解析 feed 接口全部文章，按 since_time 过滤"""
        if not isinstance(body, dict):
            return

        data_list = body.get('data', [])
        if not isinstance(data_list, list):
            return

        seen_ids = {str(a.group_id) for a in self._articles}
        new_count = 0
        filtered = 0

        for item in data_list:
            gid = str(item.get('group_id', '') or item.get('item_id', ''))
            if not gid or gid in seen_ids:
                continue

            publish_time = item.get('publish_time', 0) or item.get('behot_time', 0)

            # 时间过滤
            if self._since_time and publish_time and publish_time < self._since_time:
                filtered += 1
                continue

            article = ArticleItem(item)
            if article.title:
                self._articles.append(article)
                seen_ids.add(gid)
                new_count += 1

        log.info(f'解析完成: 新增 {new_count} 篇, 过滤 {filtered} 篇(早于时间点), 累计 {len(self._articles)} 篇')
        self._notify(f'获取到 {new_count} 篇文章', len(self._articles))

    def _notify(self, message, count):
        """触发进度通知"""
        if self._on_progress:
            try:
                self._on_progress(message, count)
            except Exception:
                pass

    def stop(self):
        """停止采集"""
        self._collecting = False

    def get_results(self):
        """获取当前采集结果"""
        return [a.to_dict() for a in self._articles]

    def get_summary(self):
        """获取采集结果摘要统计"""
        if not self._articles:
            return {
                'total': 0,
                'total_reads': 0,
                'total_likes': 0,
                'total_comments': 0,
                'total_shares': 0,
                'avg_reads': 0,
                'avg_likes': 0,
                'content_types': {},
            }

        total = len(self._articles)
        total_reads = sum(a.detail_read_count for a in self._articles)
        total_likes = sum(a.digg_count for a in self._articles)
        total_comments = sum(a.detail_comment_count for a in self._articles)
        total_shares = sum(a.share_count for a in self._articles)

        type_counts = {}
        for a in self._articles:
            t = a.content_type
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            'total': total,
            'total_reads': total_reads,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'total_shares': total_shares,
            'avg_reads': round(total_reads / total) if total else 0,
            'avg_likes': round(total_likes / total) if total else 0,
            'content_types': type_counts,
        }
