"""
Toutiao Tool - Main Entry Point
pywebview + Vue + Playwright
"""

import os
import sys
import signal
import webview
from logger import setup_logger, get_logger
from models import init_db
from api import Api

log = get_logger('main')


def get_web_path():
    """获取前端文件路径"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    web_dir = os.path.join(base_dir, 'web')

    if os.path.exists(web_dir) and os.path.isfile(os.path.join(web_dir, 'index.html')):
        return web_dir
    return None


def main():
    setup_logger()
    log.info('初始化应用...')

    init_db()
    api = Api()
    web_path = get_web_path()

    if not web_path:
        log.error('未找到前端构建文件 (backend/web/index.html)')
        print('错误: 未找到前端构建文件，请先执行 cd frontend && npm run build')
        sys.exit(1)

    log.info(f'前端路径: {web_path}')

    window = webview.create_window(
        title='Toutiao Tool',
        url=os.path.join(web_path, 'index.html'),
        js_api=api,
        width=1200,
        height=800,
        min_size=(900, 600),
        background_color='#0a0a0b',
    )

    api.set_window(window)
    log.info('pywebview 窗口已创建，启动主循环')

    webview.start(debug=False)

    log.info('窗口已关闭，清理资源...')
    api.cleanup()
    log.info('应用退出')

    # 强制退出，终结所有残留的守护线程和子进程
    os._exit(0)


if __name__ == '__main__':
    main()
