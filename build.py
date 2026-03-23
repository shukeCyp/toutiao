"""
Toutiao Tool 打包脚本
使用 PyInstaller 打包为 onedir 目录发布包
"""

import os
import sys
import platform
import subprocess
import shutil

# 设置 UTF-8 编码
if platform.system() == 'Windows':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')
FRONTEND_DIR = os.path.join(ROOT_DIR, 'frontend')
WEB_DIR = os.path.join(BACKEND_DIR, 'web')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output')

APP_NAME = 'ToutiaoTool'
PLAYWRIGHT_BROWSERS_DIR = os.path.join(ROOT_DIR, 'ms-playwright')


def build_frontend():
    """构建前端"""
    print('[BUILD] 构建前端...')
    npm_cmd = 'npm.cmd' if platform.system() == 'Windows' else 'npm'
    subprocess.check_call([npm_cmd, 'install'], cwd=FRONTEND_DIR)
    subprocess.check_call([npm_cmd, 'run', 'build'], cwd=FRONTEND_DIR)
    print('[BUILD] 前端构建完成')


def install_playwright():
    """安装 Playwright Chromium"""
    print('[BUILD] 安装 Playwright Chromium...')

    if os.path.exists(PLAYWRIGHT_BROWSERS_DIR):
        shutil.rmtree(PLAYWRIGHT_BROWSERS_DIR)
    os.makedirs(PLAYWRIGHT_BROWSERS_DIR, exist_ok=True)

    env = os.environ.copy()
    env['PLAYWRIGHT_BROWSERS_PATH'] = PLAYWRIGHT_BROWSERS_DIR
    subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'], env=env)

    print(f'[BUILD] Playwright Chromium 安装完成: {PLAYWRIGHT_BROWSERS_DIR}')


def get_playwright_browser_path():
    """获取 Playwright Chromium 浏览器路径"""
    if os.path.exists(PLAYWRIGHT_BROWSERS_DIR):
        print(f'[BUILD] Playwright browsers: {PLAYWRIGHT_BROWSERS_DIR}')
        return PLAYWRIGHT_BROWSERS_DIR

    print('[WARN] 未找到 Playwright 浏览器目录')
    return None


def validate_playwright_browser_path(browser_path):
    """校验 Playwright Chromium 是否已下载到预期目录"""
    if not browser_path or not os.path.isdir(browser_path):
        raise RuntimeError('未找到 Playwright 浏览器目录，无法继续打包')

    entries = os.listdir(browser_path)
    if not entries:
        raise RuntimeError(f'Playwright 浏览器目录为空: {browser_path}')

    chromium_dirs = [name for name in entries if name.startswith('chromium-')]
    if not chromium_dirs:
        raise RuntimeError(
            f'Playwright Chromium 未下载到预期目录: {browser_path}，当前内容: {entries}'
        )

    total_size = 0
    for root, _, files in os.walk(browser_path):
        for filename in files:
            fpath = os.path.join(root, filename)
            try:
                total_size += os.path.getsize(fpath)
            except OSError:
                pass

    size_mb = total_size / 1024 / 1024
    print(f'[BUILD] Playwright 浏览器目录校验通过: {size_mb:.1f} MB')


def get_directory_size_mb(directory):
    """计算目录总大小（MB）"""
    total_size = 0
    for root, _, files in os.walk(directory):
        for filename in files:
            fpath = os.path.join(root, filename)
            try:
                total_size += os.path.getsize(fpath)
            except OSError:
                pass
    return total_size / 1024 / 1024


def run_pyinstaller():
    """执行 PyInstaller 打包"""
    print('[BUILD] 开始 PyInstaller 打包...')

    # 收集后端所有 .py 文件作为 hidden imports
    backend_modules = []
    for f in os.listdir(BACKEND_DIR):
        if f.endswith('.py') and f != '__init__.py':
            mod = f[:-3]
            backend_modules.extend(['--hidden-import', mod])

    playwright_path = get_playwright_browser_path()
    validate_playwright_browser_path(playwright_path)

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', APP_NAME,
        '--noconfirm',
        '--clean',
        '--console',
        '--onedir',
        # 添加前端文件
        '--add-data', f'{WEB_DIR}{os.pathsep}web',
        # 收集 Playwright 所有文件
        '--collect-all', 'playwright',
    ]

    if playwright_path:
        cmd.extend(['--add-data', f'{playwright_path}{os.pathsep}ms-playwright'])

    # Hidden imports
    cmd.extend(backend_modules)
    cmd.extend([
        '--hidden-import', 'playwright',
        '--hidden-import', 'playwright.sync_api',
        '--hidden-import', 'playwright.async_api',
        '--hidden-import', 'webview',
        '--hidden-import', 'peewee',
        '--hidden-import', 'docx',
        '--hidden-import', 'PIL',
        '--hidden-import', 'requests',
    ])

    # 输出目录
    cmd.extend(['--distpath', OUTPUT_DIR])
    cmd.extend(['--workpath', os.path.join(ROOT_DIR, 'build')])
    cmd.extend(['--specpath', ROOT_DIR])

    # 入口文件
    cmd.append(os.path.join(BACKEND_DIR, 'main.py'))

    print(f'[BUILD] 命令: {" ".join(cmd)}')
    subprocess.check_call(cmd)
    print('[BUILD] PyInstaller 打包完成')

    app_dir = os.path.join(OUTPUT_DIR, APP_NAME)
    if os.path.isdir(app_dir):
        app_size_mb = get_directory_size_mb(app_dir)
        print(f'[BUILD] 发布目录大小: {app_size_mb:.1f} MB')

    print('[INFO] 已将 Playwright 浏览器目录随程序一起打包')


def main():
    # 清理输出
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    build_frontend()
    install_playwright()
    run_pyinstaller()

    print('')
    print(f'[DONE] 打包完成！输出目录: {OUTPUT_DIR}')
    for f in os.listdir(OUTPUT_DIR):
        fpath = os.path.join(OUTPUT_DIR, f)
        if os.path.isfile(fpath):
            size_mb = os.path.getsize(fpath) / 1024 / 1024
            print(f'  - {f} ({size_mb:.1f} MB)')
        else:
            print(f'  - {f}/')


if __name__ == '__main__':
    main()
