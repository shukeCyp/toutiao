"""
API 类 - 提供 pywebview JS API 接口
连接前端 Vue 界面和后端 Playwright 浏览器控制
"""

import os
import re
import json
import time
import asyncio
import threading
import webbrowser
import webview
from logger import get_logger
from browser_manager import BrowserManager
from toutiao_client import ToutiaoClient
from article_downloader import ArticleDownloader, fetch_article_elements, read_docx_elements, generate_docx, safe_filename
from rewrite_client import RewriteClient, SensitiveContentError
from models import Account, Setting, Article, save_articles, db, _write_lock
from task_manager import TaskManager

log = get_logger('api')

class Api:
    DEFAULT_SETTINGS = {
        'headless': False,
        'timeout': 30000,
        'collectTimeout': 60,
        'rewriteWorkers': 10,
        'apiBase': '',
        'apiKey': '',
        'model': '',
        'articleSavePath': '',
        'rewriteSavePath': '',
    }

    def __init__(self):
        self._window = None
        self._browser_manager = BrowserManager()
        self._toutiao_client = ToutiaoClient()
        self._settings = Setting.get_all(self.DEFAULT_SETTINGS)
        self._collect_results = []
        self._task_manager = TaskManager()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log.info('API 初始化完成')

    def _run_loop(self):
        """在独立线程中运行事件循环"""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_async(self, coro, timeout=120):
        """在事件循环中执行异步操作并等待结果"""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def set_window(self, window):
        """设置 pywebview 窗口引用"""
        self._window = window

    # ------------------------------------------
    # 浏览器控制 API
    # ------------------------------------------

    def launch_browser(self):
        """启动 Playwright Chrome 浏览器"""
        try:
            log.info('启动浏览器...')
            self._run_async(
                self._browser_manager.launch(
                    headless=self._settings.get('headless', False),
                    chrome_path=self._settings.get('chromePath', ''),
                    user_data_dir=self._settings.get('userDataDir', './browser_data'),
                )
            )
            log.info('浏览器启动成功')
            return {'success': True, 'message': '浏览器启动成功'}
        except Exception as e:
            log.error(f'浏览器启动失败: {e}')
            return {'success': False, 'message': str(e)}

    def close_browser(self):
        """关闭浏览器"""
        try:
            self._run_async(self._browser_manager.close())
            return {'success': True, 'message': '浏览器已关闭'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def navigate_to(self, url):
        """导航到指定 URL"""
        try:
            timeout = self._settings.get('timeout', 30000)
            self._run_async(self._browser_manager.navigate(url, timeout=timeout))
            return {'success': True, 'message': f'已导航到 {url}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_page_title(self):
        """获取当前页面标题"""
        try:
            title = self._run_async(self._browser_manager.get_title())
            return {'success': True, 'title': title}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def take_screenshot(self):
        """截取当前页面截图"""
        try:
            screenshot_b64 = self._run_async(self._browser_manager.screenshot())
            return {'success': True, 'screenshot': screenshot_b64}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def execute_script(self, script):
        """在页面中执行 JavaScript"""
        try:
            result = self._run_async(self._browser_manager.evaluate(script))
            return {'success': True, 'result': result}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ------------------------------------------
    # 对标账号 API（数据库存储，category 字段区分类型）
    # ------------------------------------------

    ACCOUNT_URL_PREFIX = 'https://www.toutiao.com/c/user/token/'

    def get_account_types(self):
        """获取所有账号类型（从 accounts 表的 category 去重）"""
        try:
            db.connect(reuse_if_open=True)
            rows = (Account.select(Account.category)
                    .distinct()
                    .order_by(Account.category))
            types = [r.category for r in rows if r.category]
            return {'success': True, 'types': types}
        except Exception as e:
            return {'success': False, 'message': str(e), 'types': []}

    def add_account_type(self, type_name):
        """添加新的账号类型（插入一条占位记录不需要，类型由账号的 category 决定，但为了兼容前端逻辑，检查是否已有该类型）"""
        try:
            type_name = type_name.strip()
            if not type_name:
                return {'success': False, 'message': '类型名称不能为空'}
            db.connect(reuse_if_open=True)
            exists = Account.select().where(Account.category == type_name).count() > 0
            if exists:
                return {'success': False, 'message': '该类型已存在'}
            # 插入一条空 URL 占位，标记类型存在
            with _write_lock:
                Account.create(url=f'__placeholder__{type_name}', category=type_name)
            log.info(f'创建账号类型: {type_name}')
            return {'success': True, 'message': f'类型「{type_name}」创建成功'}
        except Exception as e:
            log.error(f'创建类型失败: {e}')
            return {'success': False, 'message': str(e)}

    def remove_account_type(self, type_name):
        """删除一个账号类型及其所有账号"""
        try:
            type_name = type_name.strip()
            db.connect(reuse_if_open=True)
            with _write_lock:
                count = Account.delete().where(Account.category == type_name).execute()
            log.info(f'删除账号类型: {type_name} ({count} 条)')
            return {'success': True, 'message': f'类型「{type_name}」已删除'}
        except Exception as e:
            log.error(f'删除类型失败: {e}')
            return {'success': False, 'message': str(e)}

    def get_accounts(self, type_name):
        """读取某个类型的对标账号列表"""
        try:
            type_name = type_name.strip()
            db.connect(reuse_if_open=True)
            rows = (Account.select()
                    .where((Account.category == type_name) & (~Account.url.startswith('__placeholder__')))
                    .order_by(Account.created_at))
            accounts = [r.url for r in rows]
            return {'success': True, 'accounts': accounts}
        except Exception as e:
            return {'success': False, 'message': str(e), 'accounts': []}

    def _read_accounts(self, type_name):
        """内部方法：读取某个类型的账号 URL 列表"""
        db.connect(reuse_if_open=True)
        rows = (Account.select(Account.url)
                .where((Account.category == type_name) & (~Account.url.startswith('__placeholder__')))
                .order_by(Account.created_at))
        return [r.url for r in rows]

    def add_accounts(self, type_name, text):
        """批量添加对标账号"""
        try:
            type_name = type_name.strip()
            raw_items = [l.strip() for l in text.strip().splitlines() if l.strip()]
            if not raw_items:
                return {'success': False, 'message': '内容不能为空'}

            db.connect(reuse_if_open=True)
            existing_urls = set(self._read_accounts(type_name))

            added = []
            skipped = []
            invalid = []
            for item in raw_items:
                if not item.startswith(self.ACCOUNT_URL_PREFIX):
                    invalid.append(item)
                    continue
                if item in existing_urls:
                    skipped.append(item)
                else:
                    added.append(item)
                    existing_urls.add(item)

            if added:
                with _write_lock, db.atomic():
                    for url in added:
                        Account.create(url=url, category=type_name)
                    # 删除占位记录（如果有真实账号了）
                    Account.delete().where(
                        (Account.category == type_name) & (Account.url.startswith('__placeholder__'))
                    ).execute()

            all_accounts = self._read_accounts(type_name)

            parts = []
            if added:
                parts.append(f'成功添加 {len(added)} 个')
            if skipped:
                parts.append(f'跳过 {len(skipped)} 个重复')
            if invalid:
                parts.append(f'过滤 {len(invalid)} 个无效链接')
            msg = '，'.join(parts) if parts else '没有可添加的账号'
            log.info(f'[{type_name}] 批量添加: {msg} (输入 {len(raw_items)} 条)')

            return {
                'success': len(added) > 0 or (len(added) == 0 and len(invalid) == 0),
                'message': msg,
                'accounts': all_accounts,
                'added': len(added),
                'skipped': len(skipped),
                'invalid': len(invalid),
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def clear_accounts(self, type_name):
        """清空某个类型下的所有账号"""
        try:
            type_name = type_name.strip()
            db.connect(reuse_if_open=True)
            with _write_lock:
                Account.delete().where(
                    (Account.category == type_name) & (~Account.url.startswith('__placeholder__'))
                ).execute()
            log.info(f'清空账号类型: {type_name}')
            return {'success': True, 'message': '已清空全部账号', 'accounts': []}
        except Exception as e:
            log.error(f'清空账号失败: {e}')
            return {'success': False, 'message': str(e)}

    def remove_account(self, type_name, account):
        """删除某个类型下的一个对标账号"""
        try:
            type_name = type_name.strip()
            account = account.strip()
            db.connect(reuse_if_open=True)
            with _write_lock:
                rows = Account.delete().where(
                    (Account.category == type_name) & (Account.url == account)
                ).execute()
            if rows:
                all_accounts = self._read_accounts(type_name)
                return {'success': True, 'message': '删除成功', 'accounts': all_accounts}
            return {'success': False, 'message': '账号不存在'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ------------------------------------------
    # 通用工具 API
    # ------------------------------------------

    def open_in_browser(self, url):
        """使用系统默认浏览器打开链接"""
        try:
            webbrowser.open(url)
            return {'success': True, 'message': f'已打开: {url}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ------------------------------------------
    # 设置 API（持久化到数据库 settings 表）
    # ------------------------------------------

    def save_settings(self, settings):
        """保存设置"""
        try:
            if isinstance(settings, str):
                settings = json.loads(settings)
            self._settings.update(settings)
            Setting.save_all(self._settings)
            log.info('设置已保存')
            log.debug(f'当前设置: { {k: ("***" if "key" in k.lower() else v) for k, v in self._settings.items()} }')
            return {'success': True, 'message': '设置已保存'}
        except Exception as e:
            log.error(f'保存设置失败: {e}')
            return {'success': False, 'message': str(e)}

    def get_settings(self):
        """获取当前设置"""
        return {'success': True, 'settings': self._settings}

    def select_folder(self):
        """打开系统文件夹选择对话框，返回用户选择的路径"""
        try:
            if not self._window:
                return {'success': False, 'message': '窗口未就绪'}
            result = self._window.create_file_dialog(
                webview.FOLDER_DIALOG,
                directory='',
            )
            if result and len(result) > 0:
                folder_path = result[0]
                log.info(f'用户选择文件夹: {folder_path}')
                return {'success': True, 'path': folder_path}
            return {'success': False, 'message': '未选择文件夹'}
        except Exception as e:
            log.error(f'选择文件夹失败: {e}')
            return {'success': False, 'message': str(e)}

    # ------------------------------------------
    # 采集 API（ToutiaoClient）
    # ------------------------------------------

    def collect_account(self, account_url, since_time=0, until_time=0):
        """采集单个账号的文章数据，支持时间范围过滤 + 自动下滑加载"""
        try:
            log.info(f'开始采集: {account_url} (since={since_time}, until={until_time})')
            headless = self._settings.get('headless', False)
            collect_timeout = self._settings.get('collectTimeout', 60)

            def on_progress(message, count):
                if self._window:
                    try:
                        self._window.evaluate_js(
                            f'window.__onCollectProgress && window.__onCollectProgress({json.dumps(message)}, {count})'
                        )
                    except Exception:
                        pass

            async def _do_collect():
                if not self._toutiao_client.is_running:
                    await self._toutiao_client.launch(
                        headless=headless,
                    )
                result = await self._toutiao_client.collect_account(
                    account_url,
                    on_progress=on_progress,
                    since_time=since_time,
                    until_time=until_time,
                    timeout=collect_timeout,
                )
                return result

            articles = self._run_async(_do_collect())
            self._collect_results = articles
            summary = self._toutiao_client.get_summary()

            # 保存到数据库
            inserted, updated = save_articles(articles)

            log.info(f'采集完成: {len(articles)} 篇, 入库新增 {inserted} 更新 {updated}')
            return {
                'success': True,
                'message': f'采集完成，共 {len(articles)} 篇文章（新增 {inserted}，更新 {updated}）',
                'articles': articles,
                'summary': summary,
                'db_inserted': inserted,
                'db_updated': updated,
            }
        except Exception as e:
            log.error(f'采集失败: {e}', exc_info=True)
            return {'success': False, 'message': str(e)}

    def stop_collect(self):
        """停止采集"""
        try:
            self._toutiao_client.stop()
            log.info('采集已停止')
            return {'success': True, 'message': '已停止采集'}
        except Exception as e:
            log.error(f'停止采集失败: {e}')
            return {'success': False, 'message': str(e)}

    def close_collector(self):
        """关闭采集浏览器"""
        try:
            self._run_async(self._toutiao_client.close())
            return {'success': True, 'message': '采集浏览器已关闭'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_collect_results(self):
        """获取最近一次采集结果"""
        return {
            'success': True,
            'articles': self._collect_results,
            'summary': self._toutiao_client.get_summary(),
        }

    # ------------------------------------------
    # 批量抓取任务 API
    # ------------------------------------------

    def start_batch_collect(self, type_name, article_count=0, since_time=0, until_time=0):
        """
        启动批量采集任务（单类型）
        type_name: 账号类型
        article_count: 抓取文章数量，0 表示不限
        since_time: 时间范围起点
        until_time: 时间范围终点
        """
        try:
            type_name = type_name.strip()
            accounts = self._read_accounts(type_name)
            if not accounts:
                return {'success': False, 'message': f'类型「{type_name}」下没有账号'}

            collect_timeout = self._settings.get('collectTimeout', 60)
            headless = self._settings.get('headless', False)

            # 构建任务列表
            task_items = [
                {'url': url, 'category': type_name, 'max_articles': article_count}
                for url in accounts
            ]

            log.info(f'批量采集: type={type_name}, accounts={len(accounts)}, article_limit={article_count}, since={since_time}, until={until_time}, timeout={collect_timeout}s')
            result = self._task_manager.start_task(task_items, since_time=since_time, until_time=until_time, collect_timeout=collect_timeout, headless=headless)
            return result
        except Exception as e:
            log.error(f'启动批量采集失败: {e}')
            return {'success': False, 'message': str(e)}

    def start_multi_batch_collect(self, tasks_json, since_time=0, until_time=0):
        """
        启动多类型批量采集任务
        tasks_json: JSON 字符串或列表，每项: {type_name: str, article_count: int}
        since_time: 统一时间范围起点
        until_time: 统一时间范围终点
        """
        try:
            if isinstance(tasks_json, str):
                tasks = json.loads(tasks_json)
            else:
                tasks = tasks_json

            if not tasks:
                return {'success': False, 'message': '请至少添加一个采集类目'}

            collect_timeout = self._settings.get('collectTimeout', 60)
            headless = self._settings.get('headless', False)

            task_items = []
            type_summary_parts = []

            for task in tasks:
                type_name = task.get('type_name', '').strip()
                article_count = task.get('article_count', 0)
                if not type_name:
                    continue

                accounts = self._read_accounts(type_name)
                if not accounts:
                    log.warning(f'类型「{type_name}」下没有账号，跳过')
                    continue

                for url in accounts:
                    task_items.append({
                        'url': url,
                        'category': type_name,
                        'max_articles': article_count,
                    })

                limit_str = f'{article_count}篇' if article_count > 0 else '不限'
                type_summary_parts.append(f'{type_name}({len(accounts)}个账号, {limit_str})')

            if not task_items:
                return {'success': False, 'message': '所有类目下都没有账号'}

            type_summary = ', '.join(type_summary_parts)
            log.info(f'多类型批量采集: {type_summary}, since={since_time}, until={until_time}, timeout={collect_timeout}s')
            result = self._task_manager.start_task(task_items, since_time=since_time, until_time=until_time, collect_timeout=collect_timeout, headless=headless)
            return result
        except Exception as e:
            log.error(f'启动多类型批量采集失败: {e}')
            return {'success': False, 'message': str(e)}

    def get_task_status(self):
        """获取当前批量任务状态"""
        return self._task_manager.get_status()

    def stop_batch_task(self):
        """停止批量任务"""
        return self._task_manager.stop_task()

    # ------------------------------------------
    # 文章数据库 API
    # ------------------------------------------

    def get_articles(self, page=1, page_size=20, filter_rewritten=None):
        """分页查询文章列表"""
        try:
            db.connect(reuse_if_open=True)
            query = Article.select().order_by(Article.publish_time.desc())
            if filter_rewritten is not None:
                query = query.where(Article.is_rewritten == filter_rewritten)
            total = query.count()
            items = list(query.paginate(page, page_size))
            return {
                'success': True,
                'articles': [a.to_dict() for a in items],
                'total': total,
                'page': page,
                'page_size': page_size,
            }
        except Exception as e:
            log.error(f'查询文章失败: {e}')
            return {'success': False, 'message': str(e)}

    def toggle_rewritten(self, article_id):
        """切换文章的改写标志"""
        try:
            db.connect(reuse_if_open=True)
            article = Article.get_or_none(Article.id == article_id)
            if not article:
                return {'success': False, 'message': '文章不存在'}
            article.is_rewritten = not article.is_rewritten
            article.save()
            log.debug(f'文章 {article_id} 改写标志 -> {article.is_rewritten}')
            return {'success': True, 'is_rewritten': article.is_rewritten}
        except Exception as e:
            log.error(f'切换改写标志失败: {e}')
            return {'success': False, 'message': str(e)}

    def delete_article(self, article_id):
        """删除文章"""
        try:
            db.connect(reuse_if_open=True)
            rows = Article.delete().where(Article.id == article_id).execute()
            if rows:
                log.info(f'删除文章: id={article_id}')
                return {'success': True, 'message': '已删除'}
            return {'success': False, 'message': '文章不存在'}
        except Exception as e:
            log.error(f'删除文章失败: {e}')
            return {'success': False, 'message': str(e)}

    def get_article_stats(self):
        """获取文章统计"""
        try:
            db.connect(reuse_if_open=True)
            total = Article.select().count()
            rewritten = Article.select().where(Article.is_rewritten == True).count()
            pending = total - rewritten
            return {
                'success': True,
                'total': total,
                'rewritten': rewritten,
                'pending': pending,
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ------------------------------------------
    # 文章下载 API
    # ------------------------------------------

    def download_article(self, article_id):
        """下载文章为 docx 文档"""
        try:
            db.connect(reuse_if_open=True)
            article = Article.get_or_none(Article.id == article_id)
            if not article:
                return {'success': False, 'message': '文章不存在'}

            save_path = self._settings.get('articleSavePath', '')
            if not save_path:
                return {'success': False, 'message': '请先在设置中配置文章保存路径'}

            article_url = article.url
            if not article_url:
                return {'success': False, 'message': '文章链接为空'}

            headless = self._settings.get('headless', False)
            log.info(f'下载文章: id={article_id}, title={article.title[:30]}')

            async def _do_download():
                downloader = ArticleDownloader()
                doc_path = await downloader.download(
                    article_url=article_url,
                    save_dir=save_path,
                    category=article.category,
                    title=article.title,
                    headless=headless,
                )
                return doc_path

            doc_path = self._run_async(_do_download())

            # 更新数据库
            with _write_lock:
                Article.update(doc_path=doc_path).where(Article.id == article_id).execute()

            log.info(f'文章下载完成: {doc_path}')
            return {'success': True, 'message': '下载完成', 'doc_path': doc_path}
        except Exception as e:
            log.error(f'文章下载失败: {e}', exc_info=True)
            return {'success': False, 'message': str(e)}

    def get_download_stats(self):
        """获取下载统计"""
        try:
            db.connect(reuse_if_open=True)
            total = Article.select().count()
            downloaded = Article.select().where(Article.doc_path != '').count()
            not_downloaded = total - downloaded
            return {
                'success': True,
                'total': total,
                'downloaded': downloaded,
                'not_downloaded': not_downloaded,
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_download_articles(self, page=1, page_size=20, filter_downloaded=None):
        """分页查询文章列表（下载页面专用）"""
        try:
            db.connect(reuse_if_open=True)
            query = Article.select().order_by(Article.publish_time.desc())
            if filter_downloaded is True:
                query = query.where(Article.doc_path != '')
            elif filter_downloaded is False:
                query = query.where((Article.doc_path == '') | (Article.doc_path.is_null()))
            total = query.count()
            items = list(query.paginate(page, page_size))
            return {
                'success': True,
                'articles': [a.to_dict() for a in items],
                'total': total,
                'page': page,
                'page_size': page_size,
            }
        except Exception as e:
            log.error(f'查询下载文章失败: {e}')
            return {'success': False, 'message': str(e)}

    def batch_download_articles(self, article_ids):
        """批量下载文章（逐个下载，返回总结果）"""
        try:
            if isinstance(article_ids, str):
                article_ids = json.loads(article_ids)

            save_path = self._settings.get('articleSavePath', '')
            if not save_path:
                return {'success': False, 'message': '请先在设置中配置文章保存路径'}

            headless = self._settings.get('headless', False)

            db.connect(reuse_if_open=True)
            results = []
            success_count = 0
            fail_count = 0

            for article_id in article_ids:
                article = Article.get_or_none(Article.id == article_id)
                if not article:
                    results.append({'id': article_id, 'success': False, 'message': '文章不存在'})
                    fail_count += 1
                    continue

                if not article.url:
                    results.append({'id': article_id, 'success': False, 'message': '文章链接为空'})
                    fail_count += 1
                    continue

                try:
                    log.info(f'批量下载: id={article_id}, title={article.title[:30]}')

                    # 通知前端进度
                    if self._window:
                        try:
                            self._window.evaluate_js(
                                f'window.__onDownloadProgress && window.__onDownloadProgress({article_id}, {json.dumps(article.title[:30])}, {success_count + fail_count + 1}, {len(article_ids)})'
                            )
                        except Exception:
                            pass

                    async def _do_download():
                        downloader = ArticleDownloader()
                        doc_path = await downloader.download(
                            article_url=article.url,
                            save_dir=save_path,
                            category=article.category,
                            title=article.title,
                            headless=headless,
                        )
                        return doc_path

                    doc_path = self._run_async(_do_download())

                    with _write_lock:
                        Article.update(doc_path=doc_path).where(Article.id == article_id).execute()

                    results.append({'id': article_id, 'success': True, 'doc_path': doc_path})
                    success_count += 1
                except Exception as e:
                    log.error(f'批量下载失败: id={article_id}, err={e}')
                    results.append({'id': article_id, 'success': False, 'message': str(e)[:100]})
                    fail_count += 1

            log.info(f'批量下载完成: 成功 {success_count}, 失败 {fail_count}')
            return {
                'success': True,
                'message': f'下载完成: 成功 {success_count} 篇, 失败 {fail_count} 篇',
                'results': results,
                'success_count': success_count,
                'fail_count': fail_count,
            }
        except Exception as e:
            log.error(f'批量下载失败: {e}', exc_info=True)
            return {'success': False, 'message': str(e)}

    # ------------------------------------------
    # 文章改写 API
    # ------------------------------------------

    def rewrite_article(self, article_id):
        """改写单篇文章"""
        try:
            # 检查设置
            rewrite_path = self._settings.get('rewriteSavePath', '')
            if not rewrite_path:
                return {'success': False, 'message': '请先在设置中配置改写文章保存路径'}
            api_base = self._settings.get('apiBase', '')
            api_key = self._settings.get('apiKey', '')
            model = self._settings.get('model', '')
            if not api_base or not api_key or not model:
                return {'success': False, 'message': '请先在设置中配置模型 API 地址、秘钥和模型名称'}

            db.connect(reuse_if_open=True)
            article = Article.get_or_none(Article.id == article_id)
            if not article:
                return {'success': False, 'message': '文章不存在'}
            if not article.url:
                return {'success': False, 'message': '文章链接为空'}

            headless = self._settings.get('headless', False)
            log.info(f'改写文章: id={article_id}, title={article.title[:30]}')

            # 1. 提取文章元素：优先读本地 docx，没有则从网页抓取
            if article.doc_path and os.path.isfile(article.doc_path):
                log.info(f'从本地 docx 读取: {article.doc_path}')
                elements = read_docx_elements(article.doc_path)
            else:
                log.info(f'本地无文件，从网页抓取: {article.url}')
                async def _fetch():
                    return await fetch_article_elements(article.url, headless=headless)
                elements = self._run_async(_fetch())

            # 2. 分离文字段落
            text_indices = []
            paragraphs = []
            for i, elem in enumerate(elements):
                if elem['type'] == 'text':
                    text_indices.append(i)
                    paragraphs.append(elem['text'])

            if not paragraphs:
                return {'success': False, 'message': '文章没有可改写的文字内容'}

            # 2.5. 字数不足 1000 的文章直接删除
            total_chars = sum(len(p) for p in paragraphs)
            if total_chars < 1000:
                # #region agent log
                _dbg = '/Users/chaiyapeng/Documents/toutiao/.cursor/debug.log'
                open(_dbg, 'a').write(json.dumps({"location":"api.py:rewrite_article:delete_short","message":"文章字数不足已删除","data":{"article_id":article_id,"title":article.title[:50],"total_chars":total_chars,"reason":"total_chars < 1000"},"timestamp":int(time.time()*1000)}) + '\n')
                # #endregion
                log.info(f'文章字数不足 1000（{total_chars} 字），直接删除: id={article_id}, title={article.title[:30]}')
                with _write_lock:
                    Article.delete().where(Article.id == article_id).execute()
                return {'success': True, 'message': f'文章字数不足 1000（{total_chars} 字），已自动删除', 'deleted': True}

            # 3. 调用 LLM 改写（失败自动重试最多 3 次）
            timeout = self._settings.get('timeout', 30000) / 1000  # 毫秒转秒
            client = RewriteClient(api_base, api_key, model, timeout=timeout)

            max_retries = 3
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    new_title, new_paragraphs = client.rewrite(article.title, paragraphs)
                    last_error = None
                    break
                except SensitiveContentError as e:
                    # 敏感词等需删文的错误：不重试，直接删文
                    # #region agent log
                    _dbg = '/Users/chaiyapeng/Documents/toutiao/.cursor/debug.log'
                    open(_dbg, 'a').write(json.dumps({"location":"api.py:rewrite_article:delete_sensitive","message":"敏感词已删除","data":{"article_id":article_id,"title":article.title[:50],"reason":str(e)[:200]},"timestamp":int(time.time()*1000)}) + '\n')
                    # #endregion
                    log.info(f'内容包含敏感词，删除文章: id={article_id}, title={article.title[:30]}')
                    with _write_lock:
                        Article.delete().where(Article.id == article_id).execute()
                    return {'success': True, 'message': '内容包含敏感词，已自动删除', 'deleted': True}
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        log.warning(f'改写失败 (第 {attempt}/{max_retries} 次)，5s 后重试: {e}')
                        time.sleep(5)
                    else:
                        log.error(f'改写失败，已重试 {max_retries} 次: {e}')

            if last_error is not None:
                raise last_error

            # 4. 替换文字段落（保持图片位置不变）
            for idx, text_idx in enumerate(text_indices):
                if idx < len(new_paragraphs):
                    elements[text_idx] = {'type': 'text', 'text': new_paragraphs[idx]}

            # 5. 生成 docx 保存
            filename = safe_filename(new_title) + '.docx'
            if article.category:
                folder = os.path.join(rewrite_path, safe_filename(article.category))
            else:
                folder = rewrite_path
            save_path = os.path.join(folder, filename)

            generate_docx(elements, save_path)

            # 6. 更新数据库
            with _write_lock:
                Article.update(is_rewritten=True).where(Article.id == article_id).execute()

            log.info(f'文章改写完成: {save_path}')
            return {'success': True, 'message': '改写完成', 'save_path': save_path, 'new_title': new_title}

        except Exception as e:
            # #region agent log
            _dbg = '/Users/chaiyapeng/Documents/toutiao/.cursor/debug.log'
            open(_dbg, 'a').write(json.dumps({"location":"api.py:rewrite_article:error","message":"单篇改写失败","data":{"article_id":article_id,"error":str(e)[:200],"error_type":type(e).__name__},"timestamp":int(time.time()*1000)}) + '\n')
            # #endregion
            log.error(f'文章改写失败: {e}', exc_info=True)
            return {'success': False, 'message': str(e)}

    def batch_rewrite_articles(self, force=False):
        """批量改写文章（多线程并行）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading as _threading

        try:
            # 检查设置
            rewrite_path = self._settings.get('rewriteSavePath', '')
            if not rewrite_path:
                return {'success': False, 'message': '请先在设置中配置改写文章保存路径'}
            api_base = self._settings.get('apiBase', '')
            api_key = self._settings.get('apiKey', '')
            model = self._settings.get('model', '')
            if not api_base or not api_key or not model:
                return {'success': False, 'message': '请先在设置中配置模型 API 地址、秘钥和模型名称'}

            db.connect(reuse_if_open=True)
            if force:
                articles = list(Article.select().where(Article.url != '').order_by(Article.publish_time.desc()))
            else:
                articles = list(Article.select().where(
                    (Article.is_rewritten == False) & (Article.url != '')
                ).order_by(Article.publish_time.desc()))

            if not articles:
                return {'success': True, 'message': '没有需要改写的文章', 'success_count': 0, 'fail_count': 0}

            headless = self._settings.get('headless', False)
            total = len(articles)
            success_count = 0
            fail_count = 0
            deleted_count = 0   # 字数不足被删除
            skip_count = 0      # 无文字内容被跳过
            completed_count = 0
            counter_lock = _threading.Lock()

            REWRITE_WORKERS = self._settings.get('rewriteWorkers', 10)

            def _rewrite_worker(article):
                """单篇改写 worker，在线程池线程中执行"""
                nonlocal success_count, fail_count, deleted_count, skip_count, completed_count

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # 推送进度
                    with counter_lock:
                        completed_count += 1
                        current = completed_count
                    if self._window:
                        try:
                            self._window.evaluate_js(
                                f'window.__onRewriteProgress && window.__onRewriteProgress({current}, {total}, {json.dumps(article.title[:30])})'
                            )
                        except Exception:
                            pass

                    log.info(f'批量改写 [{current}/{total}]: {article.title[:30]}')

                    # 1. 提取元素：优先读本地 docx
                    if article.doc_path and os.path.isfile(article.doc_path):
                        log.info(f'从本地 docx 读取: {article.doc_path}')
                        elements = read_docx_elements(article.doc_path)
                    else:
                        log.info(f'本地无文件，从网页抓取: {article.url}')
                        elements = loop.run_until_complete(
                            fetch_article_elements(article.url, headless=headless)
                        )

                    # 2. 分离文字
                    text_indices = []
                    paragraphs = []
                    for idx, elem in enumerate(elements):
                        if elem['type'] == 'text':
                            text_indices.append(idx)
                            paragraphs.append(elem['text'])

                    if not paragraphs:
                        # #region agent log
                        _dbg = '/Users/chaiyapeng/Documents/toutiao/.cursor/debug.log'
                        open(_dbg, 'a').write(json.dumps({"location":"api.py:batch_rewrite:skip_no_content","message":"无文字内容跳过","data":{"article_id":article.id,"title":article.title[:50]},"timestamp":int(time.time()*1000)}) + '\n')
                        # #endregion
                        log.warning(f'文章无文字内容，跳过: id={article.id}')
                        with counter_lock:
                            skip_count += 1
                        return

                    # 2.5. 字数不足 1000 的文章直接删除
                    total_chars = sum(len(p) for p in paragraphs)
                    if total_chars < 1000:
                        # #region agent log
                        _dbg = '/Users/chaiyapeng/Documents/toutiao/.cursor/debug.log'
                        open(_dbg, 'a').write(json.dumps({"location":"api.py:batch_rewrite:delete_short","message":"字数不足已删除","data":{"article_id":article.id,"title":article.title[:50],"total_chars":total_chars,"reason":"total_chars < 1000"},"timestamp":int(time.time()*1000)}) + '\n')
                        # #endregion
                        log.info(f'文章字数不足 1000（{total_chars} 字），直接删除: id={article.id}, title={article.title[:30]}')
                        with _write_lock:
                            db.connect(reuse_if_open=True)
                            Article.delete().where(Article.id == article.id).execute()
                        with counter_lock:
                            deleted_count += 1
                        return

                    # 3. LLM 改写（失败自动重试最多 3 次）
                    timeout = self._settings.get('timeout', 30000) / 1000
                    client = RewriteClient(api_base, api_key, model, timeout=timeout)

                    max_retries = 3
                    last_error = None
                    for attempt in range(1, max_retries + 1):
                        try:
                            new_title, new_paragraphs = client.rewrite(article.title, paragraphs)
                            last_error = None
                            break
                        except SensitiveContentError as e:
                            # 敏感词等需删文的错误：不重试，直接删文
                            # #region agent log
                            _dbg = '/Users/chaiyapeng/Documents/toutiao/.cursor/debug.log'
                            open(_dbg, 'a').write(json.dumps({"location":"api.py:batch_rewrite:delete_sensitive","message":"敏感词已删除","data":{"article_id":article.id,"title":article.title[:50],"reason":str(e)[:200]},"timestamp":int(time.time()*1000)}) + '\n')
                            # #endregion
                            log.info(f'内容包含敏感词，删除文章: id={article.id}, title={article.title[:30]}')
                            with _write_lock:
                                db.connect(reuse_if_open=True)
                                Article.delete().where(Article.id == article.id).execute()
                            with counter_lock:
                                deleted_count += 1
                            return
                        except Exception as e:
                            last_error = e
                            if attempt < max_retries:
                                log.warning(f'改写失败 (第 {attempt}/{max_retries} 次)，5s 后重试: id={article.id}, err={e}')
                                time.sleep(5)
                            else:
                                log.error(f'改写失败，已重试 {max_retries} 次: id={article.id}, err={e}')

                    if last_error is not None:
                        raise last_error

                    # 4. 替换文字段落（保持图片位置不变）
                    for j, text_idx in enumerate(text_indices):
                        if j < len(new_paragraphs):
                            elements[text_idx] = {'type': 'text', 'text': new_paragraphs[j]}

                    # 5. 保存 docx
                    filename = safe_filename(new_title) + '.docx'
                    if article.category:
                        folder = os.path.join(rewrite_path, safe_filename(article.category))
                    else:
                        folder = rewrite_path
                    save_path = os.path.join(folder, filename)

                    generate_docx(elements, save_path)

                    # 6. 更新数据库
                    with _write_lock:
                        db.connect(reuse_if_open=True)
                        Article.update(is_rewritten=True).where(Article.id == article.id).execute()

                    with counter_lock:
                        success_count += 1

                    log.info(f'改写完成: {save_path}')

                except Exception as e:
                    # #region agent log
                    _dbg = '/Users/chaiyapeng/Documents/toutiao/.cursor/debug.log'
                    open(_dbg, 'a').write(json.dumps({"location":"api.py:batch_rewrite:error","message":"批量改写失败(需关注是否应删文)","data":{"article_id":article.id,"title":article.title[:50],"error":str(e)[:200],"error_type":type(e).__name__},"timestamp":int(time.time()*1000)}) + '\n')
                    # #endregion
                    log.error(f'批量改写失败: id={article.id}, err={e}', exc_info=True)
                    with counter_lock:
                        fail_count += 1
                finally:
                    loop.close()

            log.info(f'批量改写启动: {total} 篇文章, {REWRITE_WORKERS} 线程')

            with ThreadPoolExecutor(max_workers=REWRITE_WORKERS, thread_name_prefix='rewriter') as executor:
                futures = []
                for art in articles:
                    futures.append(executor.submit(_rewrite_worker, art))
                    time.sleep(1)  # 每秒提交一个任务，避免瞬间并发过高
                for f in as_completed(futures):
                    try:
                        f.result(timeout=600)
                    except Exception:
                        pass

            # 构建结果消息
            parts = [f'改写成功 {success_count} 篇']
            if deleted_count > 0:
                parts.append(f'删除 {deleted_count} 篇（字数不足或敏感词）')
            if skip_count > 0:
                parts.append(f'无内容跳过 {skip_count} 篇')
            if fail_count > 0:
                parts.append(f'失败 {fail_count} 篇')
            msg = '改写完成: ' + ', '.join(parts)

            log.info(f'批量改写完成: 成功={success_count}, 删除={deleted_count}, 跳过={skip_count}, 失败={fail_count}')
            return {
                'success': True,
                'message': msg,
                'success_count': success_count,
                'fail_count': fail_count,
                'deleted_count': deleted_count,
                'skip_count': skip_count,
            }
        except Exception as e:
            log.error(f'批量改写失败: {e}', exc_info=True)
            return {'success': False, 'message': str(e)}

    def import_article_urls(self, urls_text):
        """通过文章链接批量导入文章（一行一个链接）"""
        import re
        from datetime import datetime

        try:
            if isinstance(urls_text, str):
                raw_urls = [l.strip() for l in urls_text.strip().splitlines() if l.strip()]
            else:
                raw_urls = []

            if not raw_urls:
                return {'success': False, 'message': '请输入至少一个文章链接'}

            db.connect(reuse_if_open=True)

            added = 0
            skipped = 0
            invalid = 0
            now = datetime.now()

            with _write_lock, db.atomic():
                for url in raw_urls:
                    # 提取文章 ID，支持多种头条文章 URL 格式
                    # https://www.toutiao.com/article/7473002025927541286/
                    # https://www.toutiao.com/a7473002025927541286/
                    # https://www.toutiao.com/i7473002025927541286/
                    match = re.search(r'/article/(\d+)', url)
                    if not match:
                        match = re.search(r'/[ai](\d{10,})', url)
                    if not match:
                        match = re.search(r'(\d{15,})', url)

                    if not match:
                        invalid += 1
                        continue

                    group_id = match.group(1)

                    # 检查是否已存在
                    existing = Article.get_or_none(Article.group_id == group_id)
                    if existing:
                        skipped += 1
                        continue

                    # 规范化 URL
                    if not url.startswith('http'):
                        url = 'https://www.toutiao.com/article/' + group_id + '/'

                    Article.create(
                        group_id=group_id,
                        title=f'待下载文章 ({group_id})',
                        url=url,
                        created_at=now,
                        updated_at=now,
                    )
                    added += 1

            parts = []
            if added:
                parts.append(f'成功导入 {added} 篇')
            if skipped:
                parts.append(f'跳过 {skipped} 篇重复')
            if invalid:
                parts.append(f'过滤 {invalid} 个无效链接')
            msg = '，'.join(parts) if parts else '没有可导入的文章'

            log.info(f'导入文章: {msg} (输入 {len(raw_urls)} 条)')
            return {
                'success': added > 0,
                'message': msg,
                'added': added,
                'skipped': skipped,
                'invalid': invalid,
            }
        except Exception as e:
            log.error(f'导入文章失败: {e}', exc_info=True)
            return {'success': False, 'message': str(e)}

    def download_all_articles(self):
        """下载全部未下载的文章（10线程并发）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading as _threading

        try:
            save_path = self._settings.get('articleSavePath', '')
            if not save_path:
                return {'success': False, 'message': '请先在设置中配置文章保存路径'}

            headless = self._settings.get('headless', False)

            db.connect(reuse_if_open=True)
            articles = list(Article.select().where(
                (Article.url != '') & ((Article.doc_path == '') | (Article.doc_path.is_null()))
            ))

            if not articles:
                return {'success': True, 'message': '没有需要下载的文章', 'success_count': 0, 'fail_count': 0}

            total = len(articles)
            success_count = 0
            fail_count = 0
            completed_count = 0
            counter_lock = _threading.Lock()

            DOWNLOAD_WORKERS = 10

            def _download_worker(article):
                """单篇下载 worker"""
                nonlocal success_count, fail_count, completed_count

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    with counter_lock:
                        completed_count += 1
                        current = completed_count

                    # 通知前端进度
                    if self._window:
                        try:
                            self._window.evaluate_js(
                                f'window.__onDownloadProgress && window.__onDownloadProgress({article.id}, {json.dumps(article.title[:30])}, {current}, {total})'
                            )
                        except Exception:
                            pass

                    log.info(f'并发下载 [{current}/{total}]: {article.title[:30]}')

                    async def _do_download():
                        downloader = ArticleDownloader()
                        doc_path = await downloader.download(
                            article_url=article.url,
                            save_dir=save_path,
                            category=article.category,
                            title=article.title,
                            headless=headless,
                        )
                        return doc_path

                    doc_path = loop.run_until_complete(_do_download())

                    with _write_lock:
                        db.connect(reuse_if_open=True)
                        Article.update(doc_path=doc_path).where(Article.id == article.id).execute()

                    with counter_lock:
                        success_count += 1

                    log.info(f'下载完成: {doc_path}')

                except Exception as e:
                    log.error(f'并发下载失败: id={article.id}, err={e}')
                    with counter_lock:
                        fail_count += 1
                finally:
                    loop.close()

            log.info(f'全部下载启动: {total} 篇文章, {DOWNLOAD_WORKERS} 线程')

            with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS, thread_name_prefix='downloader') as executor:
                futures = [executor.submit(_download_worker, art) for art in articles]
                for f in as_completed(futures):
                    try:
                        f.result(timeout=300)
                    except Exception:
                        pass

            log.info(f'全部下载完成: 成功 {success_count}, 失败 {fail_count}')
            return {
                'success': True,
                'message': f'下载完成: 成功 {success_count} 篇, 失败 {fail_count} 篇',
                'success_count': success_count,
                'fail_count': fail_count,
            }
        except Exception as e:
            log.error(f'下载全部文章失败: {e}', exc_info=True)
            return {'success': False, 'message': str(e)}

    def delete_all_articles(self):
        """删除全部文章"""
        try:
            db.connect(reuse_if_open=True)
            with _write_lock:
                count = Article.delete().execute()
            log.info(f'删除全部文章: {count} 篇')
            return {'success': True, 'message': f'已删除全部 {count} 篇文章'}
        except Exception as e:
            log.error(f'删除全部文章失败: {e}')
            return {'success': False, 'message': str(e)}

    # ------------------------------------------
    # 清理
    # ------------------------------------------

    def cleanup(self):
        """清理所有资源"""
        log.info('清理资源...')
        try:
            self._run_async(self._browser_manager.close())
        except Exception:
            pass
        try:
            self._run_async(self._toutiao_client.close())
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)
        log.info('资源清理完成')
