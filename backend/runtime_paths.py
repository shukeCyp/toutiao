"""
运行时资源路径辅助
兼容 PyInstaller onefile 解包目录与源码目录
"""

import os
import sys


def is_frozen():
    """当前是否运行在 PyInstaller 打包环境中"""
    return getattr(sys, 'frozen', False)


def get_base_dir():
    """获取运行时资源根目录"""
    if is_frozen():
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(*parts):
    """拼接运行时资源路径"""
    return os.path.join(get_base_dir(), *parts)


def configure_playwright_env():
    """让 Playwright 优先使用打包进程序的浏览器内核目录"""
    browser_dir = get_resource_path('ms-playwright')
    if os.path.isdir(browser_dir):
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browser_dir
        return browser_dir
    return None
