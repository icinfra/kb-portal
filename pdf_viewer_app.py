#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 文档查看器 Flask 应用
用于浏览和查看产品手册PDF文件
"""

import os
import re
from pathlib import Path
from flask import Flask, render_template, send_file, jsonify, request, url_for
from collections import defaultdict
import mimetypes

app = Flask(__name__)

class PDFDocumentManager:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.releases = {}
        self.all_pdfs = []  # 用于搜索索引
        self.scan_documents()
    
    def scan_documents(self):
        """扫描所有PDF文件并按release组织"""
        print(f"开始扫描目录: {self.base_path}")
        
        # 扫描所有PDF文件
        pdf_files = list(self.base_path.rglob("*.pdf"))
        print(f"找到 {len(pdf_files)} 个PDF文件")
        
        for pdf_file in pdf_files:
            self.add_document(pdf_file)
        
        print(f"文档结构构建完成，共 {len(self.releases)} 个Release")
    
    def add_document(self, pdf_path):
        """添加文档到release结构中"""
        relative_path = pdf_path.relative_to(self.base_path)
        parts = relative_path.parts
        
        if len(parts) < 2:
            return
        
        # 第一级目录就是release名称
        release_name = parts[0]
        
        # 构建相对路径（去掉release名称）
        if len(parts) > 1:
            relative_in_release = '/'.join(parts[1:])
        else:
            relative_in_release = parts[-1]
        
        file_name = parts[-1]
        file_size = pdf_path.stat().st_size
        
        # 构建文档信息
        doc_info = {
            'name': file_name,
            'path': str(pdf_path),
            'relative_path': str(relative_path),
            'relative_in_release': relative_in_release,
            'size': file_size,
            'size_human': self.format_size(file_size),
            'release': release_name
        }
        
        # 按release组织
        if release_name not in self.releases:
            self.releases[release_name] = []
        
        self.releases[release_name].append(doc_info)
        self.all_pdfs.append(doc_info)
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def get_releases(self):
        """获取所有release列表"""
        return sorted(self.releases.keys())
    
    def get_release_documents(self, release):
        """获取指定release的所有文档"""
        if release in self.releases:
            return sorted(self.releases[release], key=lambda x: x['relative_in_release'])
        return []
    
    def search_documents(self, query):
        """搜索文档 - 支持分词搜索"""
        if not query or len(query.strip()) < 2:
            return []
        
        results = []
        query_terms = query.lower().split()  # 简单分词
        
        for doc in self.all_pdfs:
            # 构建搜索文本
            search_text = ' '.join([
                doc['release'].lower(),
                doc['name'].lower(),
                doc['relative_in_release'].lower()
            ])
            
            # 检查是否匹配所有搜索词
            if all(term in search_text for term in query_terms):
                results.append(doc)
        
        return sorted(results, key=lambda x: (x['release'], x['relative_in_release']))
    
    def get_stats(self):
        """获取统计信息"""
        return {
            'total_releases': len(self.releases),
            'total_pdfs': len(self.all_pdfs),
            'total_size': sum(doc['size'] for doc in self.all_pdfs)
        }

# 初始化文档管理器
doc_manager = None

@app.route('/')
def index():
    """主页 - 显示所有releases"""
    releases = doc_manager.get_releases()
    stats = doc_manager.get_stats()
    return render_template('index.html', releases=releases, stats=stats)

@app.route('/api/releases')
def api_releases():
    """获取release列表API"""
    return jsonify(doc_manager.get_releases())

@app.route('/api/release/<release>')
def api_release_documents(release):
    """获取指定release的文档列表API"""
    documents = doc_manager.get_release_documents(release)
    return jsonify(documents)

@app.route('/api/search')
def api_search():
    """搜索API"""
    query = request.args.get('q', '')
    if len(query.strip()) < 2:
        return jsonify([])
    
    results = doc_manager.search_documents(query)
    return jsonify(results)

@app.route('/release/<release>')
def view_release(release):
    """查看release页面"""
    documents = doc_manager.get_release_documents(release)
    if not documents:
        return "Release不存在", 404
    
    return render_template('release.html', release=release, documents=documents)

@app.route('/pdf/<path:file_path>')
def view_pdf(file_path):
    """查看PDF文件"""
    # 构建完整路径
    full_path = doc_manager.base_path / file_path
    
    if not full_path.exists() or not full_path.is_file():
        return "文件不存在", 404
    
    # 检查文件类型
    if not str(full_path).lower().endswith('.pdf'):
        return "不是PDF文件", 400
    
    return send_file(str(full_path), mimetype='application/pdf')

@app.route('/download/<path:file_path>')
def download_pdf(file_path):
    """下载PDF文件"""
    full_path = doc_manager.base_path / file_path
    
    if not full_path.exists() or not full_path.is_file():
        return "文件不存在", 404
    
    return send_file(str(full_path), as_attachment=True)

def init_app(base_path):
    """初始化应用和文档管理器"""
    global doc_manager
    doc_manager = PDFDocumentManager(base_path)
    return doc_manager

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PDF 文档查看器')
    parser.add_argument('--base-path', type=str, default=str(Path(__file__).parent),
                        help='PDF 文件根目录，默认为当前脚本所在目录')
    args = parser.parse_args()

    base_path = Path(args.base_path)
    if not base_path.exists() or not base_path.is_dir():
        print(f"指定的base_path目录不存在: {base_path}")
        exit(1)

    # 初始化应用
    doc_manager = init_app(base_path)
    stats = doc_manager.get_stats()
    print("启动Flask应用...")
    print(f"服务地址: http://localhost:5000")
    print(f"文档目录: {base_path}")
    print(f"Release数量: {stats['total_releases']}")
    print(f"PDF文件数量: {stats['total_pdfs']}")
    print(f"总大小: {doc_manager.format_size(stats['total_size'])}")
    app.run(debug=True, host='0.0.0.0', port=5000)
