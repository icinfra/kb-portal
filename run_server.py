#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - PDF文档查看器
"""

import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入Flask应用
from pdf_viewer_app import app, init_app

def main():
    import argparse
    print("=" * 60)
    print("PDF文档查看器启动脚本")
    print("=" * 60)

    parser = argparse.ArgumentParser(description='PDF 文档查看器启动脚本')
    parser.add_argument('--base-path', type=str, default=str(current_dir),
                        help='PDF 文件根目录，默认为当前脚本所在目录')
    args = parser.parse_args()

    base_path = Path(args.base_path)
    if not base_path.exists() or not base_path.is_dir():
        print(f"指定的base_path目录不存在: {base_path}")
        sys.exit(1)

    print(f"扫描目录: {base_path}")

    # 初始化文档管理器
    print("初始化文档管理器...")
    doc_manager = init_app(base_path)

    print("=" * 60)
    print("启动信息:")
    print(f"- 服务地址: http://localhost:5000")
    print(f"- 服务地址: http://127.0.0.1:5000")
    print(f"- 文档目录: {base_path}")
    # 兼容旧代码，如果没有 get_products 方法则显示 release 数量
    if hasattr(doc_manager, 'get_products'):
        print(f"- 产品数量: {len(doc_manager.get_products())}")
    elif hasattr(doc_manager, 'get_releases'):
        print(f"- Release数量: {len(doc_manager.get_releases())}")
    print("=" * 60)
    print("按 Ctrl+C 停止服务")
    print("=" * 60)

    try:
        # 启动Flask应用
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
