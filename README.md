# Toutiao Tool

基于 **pywebview + Vue 3 + Playwright** 的头条文章采集与改写工具，提供 Linear 风格暗色主题桌面应用。

## 功能特性

- 📊 **账号数据采集** - 监听头条账号主页 API，批量采集文章数据（标题、阅读量、点赞数等）
- 📥 **文章下载** - 自动提取文章正文和图片，生成 Word 文档（支持头条、慧文、人民网）
- ✍️ **AI 改写** - 调用 OpenAI 兼容 API 批量改写文章，保持原创度 70%+
- 🔐 **账号管理** - 保存多个头条账号 Cookie，快速切换登录状态
- 🎯 **任务管理** - 支持批量任务队列，实时查看进度和日志
- 🌐 **代理支持** - 配置代理池，自动检测可用代理进行文章抓取
- 🖥️ **桌面应用** - 打包为独立可执行程序

## 项目结构

```
toutiao/
├── backend/                    # Python 后端
│   ├── main.py                # 应用入口
│   ├── api.py                 # JS API 接口层
│   ├── models.py              # 数据库模型（账号、文章、设置）
│   ├── browser_manager.py     # Playwright 浏览器管理
│   ├── toutiao_client.py      # 头条文章采集客户端
│   ├── article_downloader.py  # 文章下载器（提取正文+图片）
│   ├── rewrite_client.py      # AI 改写客户端
│   ├── task_manager.py        # 任务队列管理
│   ├── fingerprint.py         # 浏览器指纹生成
│   ├── logger.py              # 日志系统
│   └── web/                   # Vue 构建输出（自动生成）
├── frontend/                  # Vue 3 前端
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   │   ├── Home.vue      # 首页
│   │   │   ├── Accounts.vue  # 账号管理
│   │   │   ├── Articles.vue  # 文章采集
│   │   │   ├── Downloads.vue # 下载管理
│   │   │   ├── Settings.vue  # 设置
│   │   │   └── Debug.vue     # 调试工具
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── router.js         # 路由配置
│   │   └── main.js           # 入口文件
│   ├── package.json
│   └── vite.config.js
├── database/                  # SQLite 数据库文件
├── logs/                      # 应用日志
├── data/                      # 数据文件
├── build.py                   # 打包脚本
├── requirements.txt           # Python 依赖
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt
playwright install chromium

# 前端依赖
cd frontend && npm install && cd ..
```

### 2. 开发模式

分两个终端运行：

```bash
# 终端 1 - 前端开发服务器
cd frontend && npm run dev

# 终端 2 - 启动桌面应用
cd backend && python main.py
```

### 3. 生产模式

```bash
# 构建前端
cd frontend && npm run build && cd ..

# 运行应用
cd backend && python main.py
```

### 4. 打包发布

```bash
# 打包为独立可执行程序
python build.py

# 输出目录: output/
# Windows: output/ToutiaoTool/ToutiaoTool.exe
```

## 使用指南

### 账号管理
1. 打开应用，进入「账号管理」页面
2. 点击「添加账号」，输入账号名称和头条 Cookie
3. 保存后可在采集时选择使用该账号登录状态

### 文章采集
1. 进入「文章采集」页面
2. 输入头条账号主页 URL（如 `https://www.toutiao.com/c/user/...`）
3. 选择登录账号（可选）
4. 设置采集超时时间，点击「开始采集」
5. 采集完成后可查看文章列表，支持导出和批量下载

### 文章下载
1. 在采集结果中勾选需要下载的文章
2. 点击「批量下载」，设置保存路径
3. 工具会自动提取正文和图片，生成 Word 文档
4. 支持头条、慧文、人民网等多个平台

### AI 改写
1. 在「设置」中配置 OpenAI 兼容 API（API Base、API Key、模型）
2. 设置改写并发数和保存路径
3. 在文章列表中选择需要改写的文章
4. 点击「批量改写」，自动调用 AI 改写标题和正文
5. 改写后的文档会保存到指定目录

### 代理配置
1. 在「设置」中配置代理池（每行一个代理）
2. 格式：`IP:端口 用户名 密码`（用户名密码可选）
3. 工具会自动检测可用代理并使用

## 技术栈

| 层级   | 技术              | 说明                         |
| ------ | ----------------- | ---------------------------- |
| 前端   | Vue 3 + Vite      | SPA 界面，Composition API    |
| 状态   | Pinia             | 状态管理                     |
| 路由   | Vue Router 4      | Hash 模式路由                |
| 后端   | pywebview         | 桌面窗口，前后端通信桥梁     |
| 浏览器 | Playwright        | Chrome 浏览器自动化          |
| 数据库 | Peewee + SQLite   | 本地数据持久化               |
| 文档   | python-docx       | Word 文档生成                |
| UI     | 自定义 CSS        | Linear 设计风格，暗色主题    |

## 前后端通信

前端通过 `window.pywebview.api` 调用 Python 后端方法：

```javascript
// 采集文章
await window.pywebview.api.collect_articles(url, accountId, timeout)

// 下载文章
await window.pywebview.api.download_article(url, title, category)

// 改写文章
await window.pywebview.api.rewrite_articles(articleIds)
```

## 核心功能说明

### 文章采集原理
- 使用 Playwright 打开头条账号主页
- 监听 `/api/pc/list/feed` 和 `/api/pc/list/user/feed` 接口
- 自动滚动页面触发分页加载
- 解析 API 响应，提取文章数据（标题、URL、阅读量、点赞数等）
- 支持使用账号 Cookie 获取登录状态下的数据

### 文章下载原理
- 使用 Playwright 打开文章页面
- 根据域名自动选择对应的内容选择器
  - 头条：`.article-content`
  - 慧文：`.yl-content`
  - 人民网：`article`
- 解析 HTML，提取文字段落和图片 URL
- 下载图片并裁剪水印（头条文章）
- 生成 Word 文档，保持原文排版

### AI 改写原理
- 调用 OpenAI 兼容 API（支持 DeepSeek、通义千问等）
- 使用 Markdown 格式交互，避免 JSON 解析问题
- 逐段改写，保持段落数量一致
- 过滤 AI 痕迹词汇，保持自然口语化风格
- 支持批量并发改写，提高效率

## 注意事项

- 首次运行需要下载 Chromium 浏览器（约 300MB）
- 采集文章需要有效的头条账号 Cookie
- 改写功能需要配置 OpenAI 兼容 API
- 代理池中的代理会自动检测可用性
- 数据库文件保存在 `database/` 目录
- 日志文件保存在 `logs/` 目录

## 常见问题

**Q: 如何获取头条账号 Cookie？**
A: 在浏览器中登录头条，打开开发者工具（F12），在 Network 标签中找到任意请求，复制 Cookie 请求头的值。

**Q: 支持哪些文章来源？**
A: 目前支持今日头条（toutiao.com）、慧文（huiwen.co）、人民网（m2.people.cn）。

**Q: 改写后的文章原创度如何？**
A: 使用精心设计的 Prompt，改写后原创度可达 70% 以上，同时保持自然口语化风格。

**Q: 可以使用哪些 AI 模型？**
A: 支持所有 OpenAI 兼容 API，如 DeepSeek、通义千问、Moonshot、智谱 GLM 等。

## 开发相关

### 依赖版本
- Python >= 3.8
- Node.js >= 16
- Vue 3.5+
- Playwright 1.50+

### 开发调试
- 前端开发服务器：`http://localhost:5173`
- 后端日志：`logs/app.log`
- 数据库：`database/toutiao.db`（SQLite）

## 许可证

MIT License

## 免责声明

本工具仅供学习交流使用，请勿用于商业用途。使用本工具采集和改写文章时，请遵守相关法律法规和平台规则。
