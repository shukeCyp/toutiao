"""
ToutiaoClient - 头条对标账号数据采集客户端
使用 Playwright 打开账号主页，监听 feed 接口，解析文章数据
"""

import json
import time as _time
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from logger import get_logger
from fingerprint import random_fingerprint

log = get_logger('collector')


# 目标 API 地址（首页热门 + 用户文章列表分页）
FEED_API_URLS = [
    '/api/pc/list/feed',
    '/api/pc/list/user/feed',
]


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
        self._since_time = 0       # 时间范围起点（最早）
        self._until_time = 0       # 时间范围终点（最晚）
        self._reached_time_boundary = False  # 是否已滚动到 since_time 之前的文章

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

    async def collect_account(self, account_url, on_progress=None, since_time=0, until_time=0, timeout=60, **_kwargs):
        """
        采集单个账号的文章数据
        打开页面，拦截 feed 接口数据。设置了时间范围时会持续下滑加载，
        直到遇到早于 since_time 的文章或没有更多数据为止。

        Args:
            account_url: 账号主页链接
            on_progress: 进度回调 (message: str, count: int)
            since_time: 时间范围起点 (Unix 时间戳)，只采集该时间之后的文章，0 = 不限
            until_time: 时间范围终点 (Unix 时间戳)，只采集该时间之前的文章，0 = 不限
            timeout: 采集超时时间（秒），默认 60 秒

        Returns:
            list[dict]: 时间范围内的文章列表
        """
        if not self._page:
            raise RuntimeError('浏览器未启动，请先调用 launch()')

        self._articles = []
        self._feed_responses = []
        self._collecting = True
        self._on_progress = on_progress
        self._since_time = since_time
        self._until_time = until_time
        self._has_more = True
        self._reached_time_boundary = False

        loop = asyncio.get_running_loop()
        self._feed_received = loop.create_future()

        since_str = datetime.fromtimestamp(since_time).strftime('%Y-%m-%d %H:%M:%S') if since_time else '不限'
        until_str = datetime.fromtimestamp(until_time).strftime('%Y-%m-%d %H:%M:%S') if until_time else '不限'
        log.info(f'开始采集: {account_url}')
        log.info(f'参数: since={since_str}, until={until_str}, timeout={timeout}s')

        # 页面加载超时：120 秒
        page_timeout = 120000

        # 注册网络响应监听（必须在 goto 之前注册）
        self._page.on('response', self._on_response)

        try:
            self._notify('正在打开账号页面...', 0)
            await self._page.goto(account_url, wait_until='load', timeout=page_timeout)

            self._notify('等待 Feed 数据...', 0)

            # 等待首次 feed 数据
            try:
                await asyncio.wait_for(asyncio.shield(self._feed_received), timeout=15)
            except asyncio.TimeoutError:
                log.warning('首次等待超时，额外等待 5 秒...')
                await self._page.wait_for_timeout(5000)

            # 持续下滑加载：设了时间范围且未到达边界时，始终尝试滚动
            need_scroll = (since_time or until_time) and not self._reached_time_boundary
            log.info(f'首页数据获取完成: articles={len(self._articles)}, has_more={self._has_more}, reached_boundary={self._reached_time_boundary}, need_scroll={need_scroll}')

            if need_scroll:
                scroll_start = _time.monotonic()
                # 滚动时间预算 = 总超时 - 10秒（页面加载开销）
                scroll_budget = max(timeout - 10, 15)
                scroll_count = 0

                while (self._collecting
                       and not self._reached_time_boundary
                       and (_time.monotonic() - scroll_start) < scroll_budget):

                    scroll_count += 1
                    self._notify(f'下滑加载中 (第{scroll_count}页)... 已获取 {len(self._articles)} 篇', len(self._articles))

                    # 创建新 future 等待下一个 feed 响应
                    self._feed_received = loop.create_future()

                    # 模拟人工鼠标滚轮下滑
                    await self._scroll_to_bottom()

                    # 等待 feed 响应
                    try:
                        await asyncio.wait_for(asyncio.shield(self._feed_received), timeout=10)
                    except asyncio.TimeoutError:
                        # 第一次超时再试一次滚动
                        log.info(f'第 {scroll_count} 次滚动未触发加载，重试...')
                        self._feed_received = loop.create_future()
                        await self._scroll_to_bottom()
                        try:
                            await asyncio.wait_for(asyncio.shield(self._feed_received), timeout=8)
                        except asyncio.TimeoutError:
                            log.info('重试仍超时，停止滚动')
                            break

                    # 滚动间隔，避免请求过快
                    await self._page.wait_for_timeout(1000)

                elapsed = round(_time.monotonic() - scroll_start, 1)
                if self._reached_time_boundary:
                    log.info(f'已到达时间边界，停止滚动 (共 {scroll_count} 次滚动, {elapsed}s)')
                elif not self._collecting:
                    log.info(f'采集被停止 (共 {scroll_count} 次滚动, {elapsed}s)')
                else:
                    log.warning(f'滚动超时 ({elapsed}s), 共 {scroll_count} 次滚动')

            self._notify(f'采集完成，共 {len(self._articles)} 篇文章', len(self._articles))

        finally:
            self._page.remove_listener('response', self._on_response)
            self._collecting = False

        log.info(f'数据已获取，关闭浏览器。共 {len(self._articles)} 篇')
        await self.close()

        return [a.to_dict() for a in self._articles]

    async def _on_response(self, response):
        """监听网络响应，拦截 feed 接口，拿到数据后立即解析并通知完成"""
        try:
            url = response.url
            if not any(u in url for u in FEED_API_URLS):
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
        """解析 feed 接口全部文章，按时间范围过滤，检测时间边界"""
        if not isinstance(body, dict):
            return

        # 更新 has_more 标志
        self._has_more = body.get('has_more', False)

        data_list = body.get('data', [])
        if not isinstance(data_list, list):
            return

        seen_ids = {str(a.group_id) for a in self._articles}
        new_count = 0
        filtered_older = 0
        filtered_newer = 0

        for item in data_list:
            gid = str(item.get('group_id', '') or item.get('item_id', ''))
            if not gid or gid in seen_ids:
                continue

            publish_time = item.get('publish_time', 0) or item.get('behot_time', 0)

            # 检测时间边界：文章早于 since_time，标记到达边界
            if self._since_time and publish_time and publish_time < self._since_time:
                self._reached_time_boundary = True
                filtered_older += 1
                continue

            # 过滤晚于 until_time 的文章（太新，不在范围内）
            if self._until_time and publish_time and publish_time > self._until_time:
                filtered_newer += 1
                continue

            article = ArticleItem(item)
            if article.title:
                self._articles.append(article)
                seen_ids.add(gid)
                new_count += 1

        parts = [f'新增 {new_count} 篇']
        if filtered_older > 0:
            parts.append(f'过滤 {filtered_older} 篇(早于范围)')
        if filtered_newer > 0:
            parts.append(f'过滤 {filtered_newer} 篇(晚于范围)')
        parts.append(f'累计 {len(self._articles)} 篇')
        parts.append(f'has_more={self._has_more}')
        log.info(f'解析完成: {", ".join(parts)}')
        self._notify(f'获取到 {new_count} 篇文章', len(self._articles))

    async def _scroll_to_bottom(self):
        """模拟人工鼠标滚轮下滑，触发页面无限加载"""
        try:
            for _ in range(3):
                await self._page.mouse.wheel(0, 800)
                await self._page.wait_for_timeout(200)
        except Exception as e:
            log.warning(f'滚动操作异常: {e}')

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
