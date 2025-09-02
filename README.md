# KB Portal

知识库门户 - 一个用于管理和展示技术文档的 Web 门户系统。

<img width="1117" height="819" alt="image" src="https://github.com/user-attachments/assets/ab4a1332-77ff-4942-8e3f-ed15ccdc8bfd" />


## 项目简介

KB Portal 是 ICInfra 组织开发的知识库管理系统，旨在为团队提供统一的技术文档管理和展示平台。该项目专注于 EDA 工具、基础设施管理和技术知识的整理与分享。

## 特性

- 📚 **文档管理** - 支持多种格式的技术文档存储和管理
- 🔍 **智能搜索** - 快速查找相关技术资料和文档
- 📱 **响应式设计** - 适配桌面和移动设备
- 🔐 **权限控制** - 灵活的文档访问权限管理
- 📊 **分类体系** - 清晰的文档分类和标签系统

## 技术栈

- **前端**: HTML, CSS, JavaScript
- **部署**: GitHub Pages (支持)

## 快速开始

### 克隆仓库

```bash
git clone https://github.com/icinfra/kb-portal.git
cd kb-portal
```

### 本地开发

```bash
# 使用简单的 HTTP 服务器
python3 run_server.py --base-path /path/to/www.icinfra.cn/ProdcuManual
```

访问 `http://localhost:8000` 查看项目。

## 项目结构

```
kb-portal/
├── index.html          # 主页面
├── assets/            # 静态资源
│   ├── css/          # 样式文件
│   ├── js/           # JavaScript 文件
│   └── images/       # 图片资源
├── docs/             # 文档内容
├── components/       # 可复用组件
└── README.md        # 项目说明
```

## 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 文档贡献

- 文档应使用 Markdown 格式编写
- 请确保文档结构清晰，包含适当的标题和目录
- 代码示例应包含必要的注释
- 添加新文档时请更新相应的导航和索引

## 相关项目

- [icinfra.github.io](https://github.com/icinfra/icinfra.github.io) - ICInfra 官方网站
- [license-manager](https://github.com/icinfra/license-manager) - 许可证管理工具
- [CDS-Downloader-Suite](https://github.com/icinfra/CDS-Downloader-Suite) - CDS 工具下载套件

## 许可证

本项目目前未指定具体许可证。有关使用权限，请联系项目维护者。

## 联系我们

- **GitHub**: [@icinfra](https://github.com/icinfra)
- **Issues**: [项目问题追踪](https://github.com/icinfra/kb-portal/issues)
- **Discussions**: [社区讨论](https://github.com/icinfra/icinfra-discussions)

## 更新日志

### v1.0.0 (2025-08-25)
- 🎉 初始版本发布
- ✨ 基础知识库门户功能
- 📱 响应式界面设计

---

**Made with ❤️ by ICInfra Team**
