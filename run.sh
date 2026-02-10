#!/bin/bash
set -e

# ============================================
# Toutiao Tool 启动脚本
# 使用 uv 管理虚拟环境和依赖
# ============================================

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_DIR="$ROOT_DIR/backend"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ------------------------------------------
# 1. 检查 uv 是否安装
# ------------------------------------------
if ! command -v uv &> /dev/null; then
    err "未检测到 uv，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv &> /dev/null; then
        err "uv 安装失败，请手动安装: https://docs.astral.sh/uv/"
        exit 1
    fi
    ok "uv 安装完成"
fi
info "uv 版本: $(uv --version)"

# ------------------------------------------
# 2. 创建/同步虚拟环境 + 安装 Python 依赖
# ------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    info "创建虚拟环境..."
    uv venv "$VENV_DIR"
    ok "虚拟环境创建完成: $VENV_DIR"
fi

info "安装 Python 依赖..."
uv pip install -r "$ROOT_DIR/requirements.txt" --python "$VENV_DIR/bin/python"
ok "Python 依赖安装完成"

# ------------------------------------------
# 3. 安装 Playwright 浏览器
# ------------------------------------------
info "检查 Playwright Chromium..."
"$VENV_DIR/bin/python" -c "
from playwright.sync_api import sync_playwright
try:
    p = sync_playwright().start()
    p.chromium.launch(headless=True).close()
    p.stop()
except Exception:
    import subprocess, sys
    print('正在安装 Chromium...')
    subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])
"
ok "Playwright Chromium 就绪"

# ------------------------------------------
# 4. 安装前端依赖 & 构建
# ------------------------------------------
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    info "安装前端依赖..."
    cd "$FRONTEND_DIR"
    npm install
    ok "前端依赖安装完成"
fi

info "构建前端..."
cd "$FRONTEND_DIR"
npm run build
ok "前端构建完成"

# ------------------------------------------
# 5. 解析启动模式
# ------------------------------------------
MODE="${1:-prod}"

case "$MODE" in
    dev)
        info "以开发模式启动..."
        echo ""
        warn "请在另一个终端先运行: cd frontend && npm run dev"
        echo ""
        cd "$BACKEND_DIR"
        "$VENV_DIR/bin/python" main.py
        ;;
    build)
        info "仅构建前端..."
        cd "$FRONTEND_DIR"
        npm run build
        ok "构建完成，输出目录: $BACKEND_DIR/web/"
        ;;
    *)
        info "以生产模式启动..."
        cd "$BACKEND_DIR"
        "$VENV_DIR/bin/python" main.py
        ;;
esac
