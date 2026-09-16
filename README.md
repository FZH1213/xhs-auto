# 小红书自动发布系统

## 项目简介
自动生成小红书图文内容，提供可视化Web界面，一键发布到小红书平台。

## 🚀 快速开始（推荐）

### 方式一：一键启动（最简单）

**Mac/Linux:**
```bash
./start.sh
```

**Windows:**
```cmd
双击 start.bat
```

启动后自动打开浏览器访问：http://localhost:8000

### 方式二：手动启动

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **启动Web界面**
```bash
python main.py web
```

3. **访问界面**
打开浏览器访问：http://localhost:8000

### 首次使用配置

1. 在Web界面点击右上角「设置」
2. 填入你的AI API密钥（Claude 或 OpenAI）
3. 点击保存
4. 开始生成内容！

## 功能特性

### ✅ 已实现
- 🎨 AI自动生成小红书风格内容
- 📝 可视化Web界面
- 🗂️ 草稿管理系统
- ✏️ 在线编辑内容
- ✅ 审核确认机制
- 📊 统计数据展示

### 🚧 开发中
- 🚀 一键发布到小红书
- ⏰ 定时生成/发布
- 📷 图片AI生成
- 🔄 批量操作

## 项目结构
```
小红书自动发布/
├── config/              # 配置文件
│   ├── config.yaml      # 系统配置
│   └── prompts.yaml     # AI提示词模板
├── data/
│   ├── drafts.db        # SQLite数据库
│   └── images/          # 图片存储
├── src/
│   ├── generator/       # 内容生成模块
│   ├── storage/         # 数据存储模块
│   ├── publisher/       # 发布模块
│   └── web/             # Web审核界面
└── main.py              # 主程序入口
```