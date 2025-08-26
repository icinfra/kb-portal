#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 文档查看器 Flask 应用
用于浏览和查看产品手册PDF文件
"""

import os
import re
from pathlib import Path
from flask import Flask, render_template, send_file, jsonify, request, url_for, g, redirect
from collections import defaultdict
import mimetypes
import datetime

app = Flask(__name__)

# 默认用户信息（作为后备）
DEFAULT_USER = os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))

@app.before_request
def before_request():
    """在每个请求前执行"""
    # 从多个来源获取用户信息，按优先级排序
    user = (
        request.headers.get('X-User') or           # 1. 请求头
        request.cookies.get('user') or             # 2. Cookie
        request.args.get('user') or                # 3. URL参数
        DEFAULT_USER                               # 4. 服务器环境变量（后备）
    )
    
    g.user = user
    g.request_time = datetime.datetime.now()

@app.context_processor
def inject_user():
    """向所有模板注入用户信息"""
    return {
        'current_user': getattr(g, 'user', DEFAULT_USER),
        'request_time': getattr(g, 'request_time', datetime.datetime.now())
    }

@app.after_request
def after_request(response):
    """在每个请求完成后执行 - 自定义HTTP访问日志"""
    end_time = datetime.datetime.now()
    duration = (end_time - g.request_time).total_seconds() * 1000  # 毫秒
    
    # 自定义格式的HTTP访问日志
    print(f"[HTTP] {g.request_time.strftime('%Y-%m-%d %H:%M:%S')} | "
          f"User: {g.user} | "
          f"IP: {request.remote_addr or 'Unknown'} | "
          f"{request.method} {request.path} | "
          f"Status: {response.status_code} | "
          f"Duration: {duration:.1f}ms")
    
    return response

class PDFDocumentManager:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.releases = {}
        self.release_zips = {}  # 存储zip文件信息
        self.all_pdfs = []  # 用于搜索索引
        self.scan_documents()
    
    def scan_documents(self):
        """扫描所有PDF文件和ZIP文件并按release组织"""
        print(f"开始扫描目录: {self.base_path}")
        
        # 扫描所有PDF文件
        pdf_files = list(self.base_path.rglob("*.pdf"))
        print(f"找到 {len(pdf_files)} 个PDF文件")
        
        for pdf_file in pdf_files:
            self.add_document(pdf_file)
        
        # 扫描release级别的ZIP文件
        self.scan_release_zips()
        
        print(f"文档结构构建完成，共 {len(self.releases)} 个Release")
        print(f"找到 {len(self.release_zips)} 个Release ZIP文件")
    
    def scan_release_zips(self):
        """扫描与release同级的ZIP文件"""
        zip_files = list(self.base_path.glob("*.zip"))
        
        for zip_file in zip_files:
            zip_name = zip_file.stem  # 不包含扩展名的文件名
            
            # 检查是否存在同名的release目录
            release_dir = self.base_path / zip_name
            if not release_dir.exists() or not release_dir.is_dir():
                # 如果没有同名目录，则添加这个ZIP文件
                self.release_zips[zip_name] = {
                    'name': zip_file.name,
                    'path': str(zip_file),
                    'size': zip_file.stat().st_size,
                    'size_human': self.format_size(zip_file.stat().st_size),
                    'is_zip': True
                }
    
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
        """获取所有release列表，包括zip文件"""
        return sorted(self.releases.keys())
    
    def get_all_releases_with_zips(self):
        """获取所有release和zip文件的统一列表"""
        all_releases = []
        
        # 添加正常的release目录
        for release_name in sorted(self.releases.keys()):
            all_releases.append({
                'name': release_name,
                'type': 'directory',
                'is_zip': False,
                'doc_count': len(self.releases[release_name])
            })
        
        # 添加独立的zip文件
        for zip_name, zip_info in sorted(self.release_zips.items()):
            all_releases.append({
                'name': zip_name,
                'type': 'zip',
                'is_zip': True,
                'size_human': zip_info['size_human'],
                'zip_path': zip_info['path']
            })
        
        return all_releases
    
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
    """主页 - 显示所有releases和zip文件"""
    releases = doc_manager.get_all_releases_with_zips()
    stats = doc_manager.get_stats()
    stats['total_releases_with_zips'] = len(releases)
    stats['total_zip_files'] = len(doc_manager.release_zips)
    
    return render_template('index.html', releases=releases, stats=stats)

@app.route('/api/releases')
def api_releases():
    """获取release列表API"""
    return jsonify(doc_manager.get_releases())

@app.route('/api/user', methods=['GET', 'POST'])
def api_user():
    """用户信息API"""
    if request.method == 'POST':
        # 设置用户信息
        data = request.get_json()
        if data and 'username' in data:
            username = data['username'].strip()
            if username:
                response = jsonify({'status': 'success', 'username': username})
                response.set_cookie('user', username, max_age=30*24*60*60)  # 30天有效期
                return response
        return jsonify({'status': 'error', 'message': '用户名不能为空'}), 400
    else:
        # 获取当前用户信息
        return jsonify({'username': g.user})

@app.route('/api/detect-user')
def api_detect_user():
    """尝试自动检测用户信息"""
    # 检查多种来源
    detected_user = None
    
    # 1. 检查HTTP头中的环境变量信息
    user_from_header = request.headers.get('X-User-Env')
    if user_from_header:
        detected_user = user_from_header
    
    # 2. 检查User-Agent中的自定义信息
    user_agent = request.headers.get('User-Agent', '')
    if 'UserEnv=' in user_agent:
        try:
            start = user_agent.find('UserEnv=') + 8
            end = user_agent.find(' ', start)
            if end == -1:
                end = len(user_agent)
            detected_user = user_agent[start:end]
        except:
            pass
    
    # 3. 检查特殊的Cookie
    env_cookie = request.cookies.get('env_user')
    if env_cookie:
        detected_user = env_cookie
    
    # 4. 如果都没有，返回服务端的环境变量作为提示
    if not detected_user:
        detected_user = DEFAULT_USER
    
    return jsonify({
        'user': detected_user,
        'source': 'auto-detected',
        'methods': [
            'HTTP Header: X-User-Env',
            'User-Agent: UserEnv=username',
            'Cookie: env_user',
            'Server fallback'
        ]
    })

@app.route('/api/release/<release>')
def api_release_documents(release):
    """获取指定release的文档列表API"""
    documents = doc_manager.get_release_documents(release)
    return jsonify(documents)

@app.route('/api/search')
def api_search():
    """搜索API"""
    query = request.args.get('q', '')
    
    # 获取请求头中的用户信息
    x_user = request.headers.get('X-User', g.user)
    x_request_time = request.headers.get('X-Request-Time', '')
    
    # 额外的日志记录，显示搜索查询
    print(f"[SEARCH] User: {x_user} | Query: '{query}' | Time: {x_request_time}")
    
    if len(query.strip()) < 2:
        return jsonify([])
    
    documents = doc_manager.search_documents(query)
    
    # 转换为前端期望的格式
    results = []
    for doc in documents:
        result = {
            'doc': {
                'name': doc['name'],
                'relative_path': doc['relative_path'],
                'size_human': doc['size_human']
            },
            'product': doc['release'],  # 使用release作为product
            'version': doc['release'],  # 使用release作为version
            'module': doc['relative_in_release']  # 使用相对路径作为module
        }
        results.append(result)
    
    return jsonify(results)

@app.route('/release/<release>')
def view_release(release):
    """查看release页面"""
    # 首先检查是否是zip文件
    if release in doc_manager.release_zips:
        zip_info = doc_manager.release_zips[release]
        return render_template('zip_notice.html', 
                             release=release, 
                             zip_info=zip_info)
    
    # 正常的release目录
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
    
    # 终极解决方案：重定向stdout并过滤Werkzeug日志
    import logging
    import sys
    import re
    from io import StringIO
    
    # 禁用werkzeug logger
    logging.getLogger('werkzeug').disabled = True
    
    # 创建自定义的stdout过滤器
    class WerkzeugLogFilter:
        def __init__(self, original_stdout):
            self.original_stdout = original_stdout
            self.werkzeug_pattern = re.compile(r'^\d+\.\d+\.\d+\.\d+ - - \[.*?\] ".*?" \d+ -\s*$')
            
        def write(self, message):
            # 如果不是Werkzeug的HTTP日志格式，就正常输出
            if not self.werkzeug_pattern.match(message.strip()):
                self.original_stdout.write(message)
                
        def flush(self):
            self.original_stdout.flush()
            
        def __getattr__(self, name):
            return getattr(self.original_stdout, name)
    
    # 替换系统的stdout
    original_stdout = sys.stdout
    sys.stdout = WerkzeugLogFilter(original_stdout)
    
    print("已启用自定义日志过滤器，只显示应用自定义日志...")
    
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True, use_reloader=False)
