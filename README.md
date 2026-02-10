# Toutiao Tool

基于 **pywebview + Vue 3 + Playwright** 的桌面自动化工具，使用 Linear 风格暗色主题 UI。

## 项目结构

```
toutiao/
├── backend/                 # Python 后端
│   ├── main.py             # 入口文件 (pywebview)
│   ├── api.py              # JS API 接口层
│   ├── browser_manager.py  # Playwright 浏览器管理器
│   └── web/                # Vue 构建输出 (自动生成)
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── assets/styles/  # Linear 风格全局样式
│   │   ├── components/     # 通用组件
│   │   ├── views/          # 页面
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── router.js       # 路由配置
│   │   ├── App.vue         # 根组件
│   │   └── main.js         # 入口
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 开发模式

分两个终端运行：

**终端 1 - 启动前端 Dev Server：**

```bash
cd frontend
npm run dev
```

**终端 2 - 启动 pywebview 窗口：**

```bash
cd backend
python main.py
```

### 4. 生产构建

```bash
# 构建前端
cd frontend
npm run build

# 运行（会自动加载 backend/web/ 中的构建产物）
cd ../backend
python main.py
```

## 技术栈

| 层级   | 技术              | 说明                         |
| ------ | ----------------- | ---------------------------- |
| 前端   | Vue 3 + Vite      | SPA 界面，Composition API    |
| 状态   | Pinia             | 状态管理                     |
| 路由   | Vue Router 4      | Hash 模式路由                |
| 后端   | pywebview         | 桌面窗口，前后端通信桥梁     |
| 浏览器 | Playwright         | Chrome 浏览器自动化          |
| UI     | 自定义 CSS         | Linear 设计风格，暗色主题    |

## 前后端通信

前端通过 `window.pywebview.api` 调用 Python 后端方法：

```javascript
// 前端调用示例
const result = await window.pywebview.api.launch_browser()
const result = await window.pywebview.api.navigate_to('https://example.com')
```
