"""
Toutiao Tool 打包脚本
使用 PyInstaller 打包为单文件可执行程序
支持 Windows (.exe) 和 macOS (.app -> .dmg)
"""

import os
import sys
import platform
import subprocess
import shutil

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')
FRONTEND_DIR = os.path.join(ROOT_DIR, 'frontend')
WEB_DIR = os.path.join(BACKEND_DIR, 'web')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output')

APP_NAME = 'ToutiaoTool'


def build_frontend():
    """构建前端"""
    print('[BUILD] 构建前端...')
    subprocess.check_call(['npm', 'install'], cwd=FRONTEND_DIR)
    subprocess.check_call(['npm', 'run', 'build'], cwd=FRONTEND_DIR)
    print('[BUILD] 前端构建完成')


def install_playwright():
    """安装 Playwright Chromium"""
    print('[BUILD] 安装 Playwright Chromium...')
    subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])
    print('[BUILD] Playwright Chromium 安装完成')


def get_playwright_browser_path():
    """获取 Playwright Chromium 浏览器路径"""
    import playwright
    pw_dir = os.path.dirname(playwright.__file__)
    driver_dir = os.path.join(pw_dir, 'driver', 'package', '.local-browsers')

    if not os.path.exists(driver_dir):
        # 备选路径
        home = os.path.expanduser('~')
        if platform.system() == 'Darwin':
            driver_dir = os.path.join(home, 'Library', 'Caches', 'ms-playwright')
        elif platform.system() == 'Windows':
            driver_dir = os.path.join(home, 'AppData', 'Local', 'ms-playwright')
        else:
            driver_dir = os.path.join(home, '.cache', 'ms-playwright')

    if os.path.exists(driver_dir):
        print(f'[BUILD] Playwright browsers: {driver_dir}')
        return driver_dir

    print('[WARN] 未找到 Playwright 浏览器目录')
    return None


def run_pyinstaller():
    """执行 PyInstaller 打包"""
    print('[BUILD] 开始 PyInstaller 打包...')

    is_mac = platform.system() == 'Darwin'
    is_win = platform.system() == 'Windows'

    # 收集后端所有 .py 文件作为 hidden imports
    backend_modules = []
    for f in os.listdir(BACKEND_DIR):
        if f.endswith('.py') and f != '__init__.py':
            mod = f[:-3]
            backend_modules.extend(['--hidden-import', mod])

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', APP_NAME,
        '--noconfirm',
        '--clean',
        '--windowed',
        # 添加前端文件
        '--add-data', f'{WEB_DIR}{os.pathsep}web',
    ]

    # 添加 Playwright 浏览器
    pw_path = get_playwright_browser_path()
    if pw_path:
        cmd.extend(['--add-data', f'{pw_path}{os.pathsep}.local-browsers'])

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

    if is_mac:
        cmd.extend([
            '--osx-bundle-identifier', 'com.toutiao.tool',
        ])

    # 入口文件
    cmd.append(os.path.join(BACKEND_DIR, 'main.py'))

    print(f'[BUILD] 命令: {" ".join(cmd)}')
    subprocess.check_call(cmd)
    print('[BUILD] PyInstaller 打包完成')


def create_dmg():
    """macOS: 将 .app 打包为 .dmg"""
    app_path = os.path.join(OUTPUT_DIR, f'{APP_NAME}.app')
    dmg_path = os.path.join(OUTPUT_DIR, f'{APP_NAME}.dmg')

    if not os.path.exists(app_path):
        print(f'[WARN] 未找到 {app_path}，跳过 DMG 创建')
        return

    if os.path.exists(dmg_path):
        os.remove(dmg_path)

    print(f'[BUILD] 创建 DMG: {dmg_path}')
    subprocess.check_call([
        'hdiutil', 'create',
        '-volname', APP_NAME,
        '-srcfolder', app_path,
        '-ov',
        '-format', 'UDZO',
        dmg_path,
    ])
    print(f'[BUILD] DMG 创建完成: {dmg_path}')


def main():
    # 清理输出
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    build_frontend()
    install_playwright()
    run_pyinstaller()

    if platform.system() == 'Darwin':
        create_dmg()

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
