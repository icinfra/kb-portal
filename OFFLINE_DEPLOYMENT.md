# 离线部署说明

## 问题说明
原项目依赖在线CDN资源，在离线环境中无法正常渲染页面样式和交互功能。

## 解决方案
已将所有外部依赖本地化，包括：

### 已本地化的资源
1. **Bootstrap CSS** (v5.1.3) - `static/css/bootstrap.min.css`
2. **Bootstrap Icons** (v1.7.2) - `static/css/bootstrap-icons.css`
3. **Bootstrap JavaScript** (v5.1.3) - `static/js/bootstrap.bundle.min.js`
4. **Bootstrap Icons 字体文件** - `static/fonts/bootstrap-icons.woff` 和 `bootstrap-icons.woff2`

### 修改内容
1. 更新了 `templates/base.html` 中的资源引用路径
2. 修正了 Bootstrap Icons CSS 中的字体路径
3. 创建了完整的 `static` 目录结构

## 部署步骤

### 1. 环境准备
确保目标服务器已安装 Python 3.7+ 和 Flask：

```bash
pip install flask
```

或使用项目中的离线包：
```bash
pip install --find-links flask-packages --no-index flask
```

### 2. 文件复制
将整个项目目录复制到目标服务器，确保包含：
- `static/` 目录及其所有子文件
- `templates/` 目录
- `pdf_viewer_app.py`
- `run_server.py`
- `requirements.txt`

### 3. 启动服务
```bash
python run_server.py
```

## 验证部署
1. 启动服务后访问 `http://localhost:5000`
2. 检查页面样式是否正常显示
3. 检查图标是否正常显示
4. 检查交互功能（搜索、导航等）是否正常

## 注意事项
- 确保 `static` 目录的权限正确，Web服务需要读取权限
- 如果部署在不同端口或域名，无需额外配置
- 所有资源现在都是本地的，不依赖外部网络连接

## 故障排除
如果页面样式仍然不正常：
1. 检查浏览器开发者工具的网络面板，确认静态资源加载成功
2. 检查 Flask 应用的静态文件配置
3. 确认 `static` 目录结构完整

## 文件结构
```
kb-portal/
├── static/
│   ├── css/
│   │   ├── bootstrap.min.css
│   │   └── bootstrap-icons.css
│   ├── js/
│   │   └── bootstrap.bundle.min.js
│   └── fonts/
│       ├── bootstrap-icons.woff
│       └── bootstrap-icons.woff2
├── templates/
├── pdf_viewer_app.py
├── run_server.py
└── requirements.txt
```
