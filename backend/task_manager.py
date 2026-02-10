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

    def start_task(self, accounts, since_time=0, category='', collect_timeout=60, headless=False):
        """
        启动批量采集任务

        Args:
            accounts: 账号 URL 列表
            since_time: Unix 时间戳
            category: 分类名称
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
            self._total = len(accounts)
            self._completed = 0
            self._success = 0
            self._failed = 0
            self._total_articles = 0
            self._logs = []
            self._stop_flag = False
            self._futures = []
            self._category = category
            self._collect_timeout = collect_timeout
            self._headless = headless

        self._add_log(f'任务启动: 共 {len(accounts)} 个账号, 类型={category}, 线程池={MAX_WORKERS}, 超时={collect_timeout}s', 'info')
        if since_time:
            since_str = datetime.fromtimestamp(since_time).strftime('%Y-%m-%d %H:%M:%S')
            self._add_log(f'时间过滤: {since_str} 之后', 'info')

        log.info(f'批量任务启动: task_id={self._task_id}, accounts={len(accounts)}, since={since_time}, timeout={collect_timeout}s')

        # 提交所有账号到线程池
        for i, url in enumerate(accounts):
            if self._stop_flag:
                break
            future = self._executor.submit(self._worker, i, url, since_time)
            self._futures.append(future)

        # 启动监控线程，等所有 worker 完成后标记任务结束
        monitor = threading.Thread(target=self._monitor_completion, daemon=True)
        monitor.start()

        return {
            'success': True,
            'task_id': self._task_id,
            'total': self._total,
            'message': f'任务已启动，共 {len(accounts)} 个账号',
        }

    def _worker(self, index, account_url, since_time):
        """
        单个账号的采集 worker，在线程池线程中执行
        每个 worker 创建独立的事件循环和 ToutiaoClient
        """
        if self._stop_flag:
            return

        short_url = account_url[:80] + '...' if len(account_url) > 80 else account_url
        self._add_log(f'[{index + 1}/{self._total}] 开始采集: {short_url}', 'info')

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = ToutiaoClient()

        try:
            collect_timeout = self._collect_timeout
            headless = self._headless

            async def _do():
                await client.launch(headless=headless)
                articles = await client.collect_account(
                    account_url,
                    since_time=since_time,
                    timeout=collect_timeout,
                )
                return articles

            articles = loop.run_until_complete(_do())

            # 保存到数据库
            if articles:
                inserted, updated = save_articles(articles, category=self._category)
                with self._lock:
                    self._total_articles += len(articles)
                self._add_log(
                    f'[{index + 1}/{self._total}] 完成: {len(articles)} 篇 (新增{inserted}, 更新{updated})',
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
                        f'任务完成: 成功 {self._success}, 失败 {self._failed}, 共采集 {self._total_articles} 篇文章',
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
