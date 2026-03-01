"""
TaskManager - 批量抓取任务管理器
使用 ThreadPoolExecutor(5) 并行采集多个账号
"""

import asyncio
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from logger import get_logger
from toutiao_client import ToutiaoClient
from models import save_articles

log = get_logger('task')

# 线程池大小
MAX_WORKERS = 5


class TaskLog:
    """单条任务日志"""
    def __init__(self, message, level='info'):
        self.time = datetime.now().strftime('%H:%M:%S')
        self.message = message
        self.level = level

    def to_dict(self):
        return {'time': self.time, 'message': self.message, 'level': self.level}


class TaskManager:
    """
    批量抓取任务管理器
    同一时间只允许一个批量任务运行
    支持多类型批量采集，每个类型可设置文章数量上限
    """

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix='collector')
        self._lock = threading.Lock()

        # 当前任务状态
        self._task_id = None
        self._status = 'idle'  # idle / running / completed / failed / stopped
        self._total = 0
        self._completed = 0
        self._success = 0
        self._failed = 0
        self._total_articles = 0
        self._logs = []
        self._stop_flag = False
        self._futures = []

        # 每类目文章数量跟踪
        self._article_limits = {}        # {category: max_articles}，0 = 不限
        self._articles_per_category = {} # {category: 已采集数}

    def start_task(self, task_items, since_time=0, until_time=0, collect_timeout=60, headless=False):
        """
        启动批量采集任务

        Args:
            task_items: 任务列表，每项: {'url': str, 'category': str, 'max_articles': int}
                        max_articles: 该类目最多采集文章数，0 = 不限
            since_time: 时间范围起点 (Unix 时间戳)
            until_time: 时间范围终点 (Unix 时间戳)
            collect_timeout: 单个账号采集超时（秒），默认 60
            headless: 是否使用无头模式

        Returns:
            dict: task_id 和初始状态
        """
        with self._lock:
            if self._status == 'running':
                return {'success': False, 'message': '已有任务在运行中'}

            self._task_id = str(uuid.uuid4())[:8]
            self._status = 'running'
            self._total = len(task_items)
            self._completed = 0
            self._success = 0
            self._failed = 0
            self._total_articles = 0
            self._logs = []
            self._stop_flag = False
            self._futures = []
            self._collect_timeout = collect_timeout
            self._headless = headless
            self._until_time = until_time

            # 初始化每类目文章跟踪
            self._article_limits = {}
            self._articles_per_category = {}
            for item in task_items:
                cat = item['category']
                max_art = item.get('max_articles', 0)
                # 取最大的限制值（同一类目可能出现多次）
                if cat not in self._article_limits:
                    self._article_limits[cat] = max_art
                self._articles_per_category[cat] = 0

        # 构建类目汇总
        type_counts = {}
        for item in task_items:
            cat = item['category']
            type_counts[cat] = type_counts.get(cat, 0) + 1
        type_summary = ', '.join(f'{cat}({cnt}个账号)' for cat, cnt in type_counts.items())

        self._add_log(f'任务启动: {type_summary}, 线程池={MAX_WORKERS}, 超时={collect_timeout}s', 'info')

        # 日志：每个类目的文章数限制
        for cat, limit in self._article_limits.items():
            if limit > 0:
                self._add_log(f'  {cat}: 最多采集 {limit} 篇文章', 'info')
            else:
                self._add_log(f'  {cat}: 不限文章数量', 'info')

        if since_time and until_time:
            since_str = datetime.fromtimestamp(since_time).strftime('%Y-%m-%d %H:%M:%S')
            until_str = datetime.fromtimestamp(until_time).strftime('%Y-%m-%d %H:%M:%S')
            self._add_log(f'时间范围: {since_str} ~ {until_str}（会自动下滑加载）', 'info')
        elif since_time:
            since_str = datetime.fromtimestamp(since_time).strftime('%Y-%m-%d %H:%M:%S')
            self._add_log(f'时间过滤: {since_str} 之后（会自动下滑加载）', 'info')

        log.info(f'批量任务启动: task_id={self._task_id}, items={len(task_items)}, since={since_time}, until={until_time}, timeout={collect_timeout}s')

        # 提交所有任务到线程池
        for i, item in enumerate(task_items):
            if self._stop_flag:
                break
            future = self._executor.submit(
                self._worker, i, item['url'], since_time,
                item['category'], item.get('max_articles', 0)
            )
            self._futures.append(future)

        # 启动监控线程，等所有 worker 完成后标记任务结束
        monitor = threading.Thread(target=self._monitor_completion, daemon=True)
        monitor.start()

        return {
            'success': True,
            'task_id': self._task_id,
            'total': self._total,
            'message': f'任务已启动，{type_summary}',
        }

    def _worker(self, index, account_url, since_time, category='', max_articles=0):
        """
        单个账号的采集 worker，在线程池线程中执行
        每个 worker 创建独立的事件循环和 ToutiaoClient

        Args:
            index: 任务序号
            account_url: 账号 URL
            since_time: 时间过滤
            category: 所属类目
            max_articles: 该类目文章数上限，0 = 不限
        """
        if self._stop_flag:
            with self._lock:
                self._completed += 1
            return

        # 检查该类目是否已达文章上限
        if max_articles > 0:
            skip = False
            with self._lock:
                current = self._articles_per_category.get(category, 0)
                if current >= max_articles:
                    self._completed += 1
                    self._success += 1
                    skip = True
            if skip:
                self._add_log(f'[{index + 1}/{self._total}] 跳过: {category} 已达 {max_articles} 篇上限', 'info')
                return

        short_url = account_url[:80] + '...' if len(account_url) > 80 else account_url
        self._add_log(f'[{index + 1}/{self._total}] 开始采集: {short_url}', 'info')

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = ToutiaoClient()

        try:
            collect_timeout = self._collect_timeout
            headless = self._headless

            until_time = self._until_time

            async def _do():
                await client.launch(headless=headless)
                articles = await client.collect_account(
                    account_url,
                    since_time=since_time,
                    until_time=until_time,
                    timeout=collect_timeout,
                )
                return articles

            articles = loop.run_until_complete(_do())

            # 按类目文章上限裁剪
            if articles and max_articles > 0:
                skip_save = False
                with self._lock:
                    current = self._articles_per_category.get(category, 0)
                    remaining = max_articles - current
                    if remaining <= 0:
                        self._success += 1
                        skip_save = True
                    elif len(articles) > remaining:
                        articles = articles[:remaining]
                if skip_save:
                    self._add_log(f'[{index + 1}/{self._total}] 已达上限，跳过保存', 'info')
                    return

            # 保存到数据库
            if articles:
                inserted, updated = save_articles(articles, category=category)
                with self._lock:
                    self._total_articles += inserted
                    self._articles_per_category[category] = self._articles_per_category.get(category, 0) + len(articles)
                self._add_log(
                    f'[{index + 1}/{self._total}] 完成: 采集{len(articles)}篇, 新增{inserted}, 重复{updated}',
                    'success'
                )
            else:
                self._add_log(f'[{index + 1}/{self._total}] 完成: 无新文章', 'info')

            with self._lock:
                self._success += 1

        except Exception as e:
            log.error(f'Worker {index + 1} 失败: {e}', exc_info=True)
            self._add_log(f'[{index + 1}/{self._total}] 失败: {str(e)[:100]}', 'error')
            with self._lock:
                self._failed += 1

        finally:
            # collect_account 内部已经 close 了，这里兜底确保
            try:
                if client.is_running:
                    loop.run_until_complete(client.close())
            except Exception:
                pass
            loop.close()

            with self._lock:
                self._completed += 1

    def _monitor_completion(self):
        """监控所有 future 完成后标记任务结束"""
        # 单个 worker 的超时 = 采集超时 + 30 秒缓冲（浏览器启动/关闭）
        worker_timeout = self._collect_timeout + 30
        for f in self._futures:
            try:
                f.result(timeout=worker_timeout)
            except Exception:
                pass

        with self._lock:
            if self._status == 'running':
                if self._stop_flag:
                    self._status = 'stopped'
                    self._add_log('任务已停止', 'warning')
                else:
                    self._status = 'completed'
                    self._add_log(
                        f'任务完成: 成功 {self._success}, 失败 {self._failed}, 新增 {self._total_articles} 篇文章',
                        'success'
                    )

        log.info(f'批量任务结束: status={self._status}, success={self._success}, failed={self._failed}, articles={self._total_articles}')

    def stop_task(self):
        """停止当前任务"""
        with self._lock:
            if self._status != 'running':
                return {'success': False, 'message': '没有正在运行的任务'}
            self._stop_flag = True
            self._add_log('正在停止任务...', 'warning')

        log.info('批量任务收到停止信号')
        return {'success': True, 'message': '已发送停止信号'}

    def get_status(self):
        """获取当前任务状态"""
        with self._lock:
            return {
                'task_id': self._task_id,
                'status': self._status,
                'total': self._total,
                'completed': self._completed,
                'success': self._success,
                'failed': self._failed,
                'total_articles': self._total_articles,
                'logs': [l.to_dict() for l in self._logs[-100:]],  # 最近 100 条
                'progress': round(self._completed / self._total * 100) if self._total > 0 else 0,
            }

    def _add_log(self, message, level='info'):
        """添加日志"""
        with self._lock:
            self._logs.append(TaskLog(message, level))
            # 保留最近 500 条
            if len(self._logs) > 500:
                self._logs = self._logs[-500:]
        log.info(f'[Task] {message}')
