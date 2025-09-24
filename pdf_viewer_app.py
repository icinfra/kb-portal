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
        self.product_manual_releases = {}  # ProductManual目录下的内容
        self.knowledge_base_releases = {}  # 其他目录下的内容
        self.release_zips = {}  # 存储zip文件信息
        self.all_documents = []  # 用于搜索索引（包含所有类型文件）
        self.supported_extensions = {'.pdf', '.mhtml', '.mht', '.zip', '.rar', '.7z', '.tar', '.gz'}
        self.scan_documents()
    
    def scan_documents(self):
        """扫描所有支持的文件并按分类组织"""
        print(f"开始扫描目录: {self.base_path}")
        
        # 扫描所有支持的文件
        all_files = []
        for ext in ['.pdf', '.mhtml', '.mht', '.zip', '.rar', '.7z', '.tar', '.gz']:  # 包含所有支持的文件类型
            files = list(self.base_path.rglob(f"*{ext}"))
            all_files.extend(files)
        
        print(f"找到 {len(all_files)} 个文档文件")
        
        for file in all_files:
            self.add_document(file)
        
        # 扫描release级别的ZIP文件（根目录下的压缩包）
        self.scan_release_zips()
        
        print(f"文档结构构建完成:")
        print(f"  - Product Manual: {len(self.product_manual_releases)} 个Release")
        print(f"  - Knowledge Base: {len(self.knowledge_base_releases)} 个Release")
        print(f"  - Release ZIP文件: {len(self.release_zips)} 个")
    
    def scan_release_zips(self):
        """扫描与release同级的ZIP文件和压缩包"""
        archive_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz']
        
        for ext in archive_extensions:
            archive_files = list(self.base_path.glob(f"*{ext}"))
            
            for archive_file in archive_files:
                archive_name = archive_file.stem  # 不包含扩展名的文件名
                
                # 检查是否存在同名的release目录
                release_dir = self.base_path / archive_name
                if not release_dir.exists() or not release_dir.is_dir():
                    # 如果没有同名目录，则添加这个压缩文件
                    self.release_zips[archive_name] = {
                        'name': archive_file.name,
                        'path': str(archive_file),
                        'size': archive_file.stat().st_size,
                        'size_human': self.format_size(archive_file.stat().st_size),
                        'type': 'archive',
                        'is_zip': True
                    }
    
    def add_document(self, file_path):
        """添加文档到对应分类的release结构中"""
        relative_path = file_path.relative_to(self.base_path)
        parts = relative_path.parts
        
        if len(parts) < 2:
            return
        
        # 第一级目录决定分类
        top_level_dir = parts[0]
        
        # 判断是ProductManual还是Knowledge Base
        is_product_manual = top_level_dir.lower() == 'productmanual'
        
        # 如果是ProductManual目录下的文件
        if is_product_manual:
            # 对于ProductManual目录下的直接压缩包文件
            if len(parts) == 2 and self.get_file_type(file_path.suffix.lower()) == 'archive':
                # 这是ProductManual目录下的压缩包，创建虚拟release
                release_name = file_path.stem  # 文件名（不含扩展名）作为release名
                target_releases = self.product_manual_releases
            else:
                # ProductManual目录下的子目录文件
                if len(parts) < 3:
                    return  # 至少需要ProductManual/Release/file结构
                release_name = parts[1]  # ProductManual/Release/...
                target_releases = self.product_manual_releases
        else:
            # Knowledge Base分类
            release_name = parts[0]  # 顶级目录作为release名
            target_releases = self.knowledge_base_releases
        
        # 构建相对路径
        if is_product_manual and len(parts) >= 3:
            # ProductManual/Release/subdir/file -> subdir/file
            relative_in_release = '/'.join(parts[2:])
        elif is_product_manual and len(parts) == 2:
            # ProductManual/archive.zip -> archive.zip
            relative_in_release = parts[1]
        else:
            # Knowledge Base: TopDir/subdir/file -> subdir/file
            relative_in_release = '/'.join(parts[1:])
        
        file_name = parts[-1]
        file_size = file_path.stat().st_size
        file_ext = file_path.suffix.lower()
        
        # 确定文件类型
        file_type = self.get_file_type(file_ext)
        
        # 确定分类
        category = 'product_manual' if is_product_manual else 'knowledge_base'
        
        # 构建文档信息
        doc_info = {
            'name': file_name,
            'path': str(file_path),
            'relative_path': str(relative_path),
            'relative_in_release': relative_in_release,
            'size': file_size,
            'size_human': self.format_size(file_size),
            'release': release_name,
            'type': file_type,
            'category': category,  # 添加分类信息
            'modified': datetime.datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'absolute_path': str(file_path.absolute())
        }
        
        # 按分类和release组织
        if release_name not in target_releases:
            target_releases[release_name] = []
        
        target_releases[release_name].append(doc_info)
        self.all_documents.append(doc_info)
    
    def get_file_type(self, ext):
        """根据扩展名返回文件类型"""
        ext = ext.lower()
        if ext == '.pdf':
            return 'pdf'
        elif ext in ['.mhtml', '.mht']:
            return 'mhtml'
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return 'archive'
        else:
            return 'unknown'
    
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
    
    def get_releases(self, category='product_manual'):
        """获取指定分类的release列表"""
        if category == 'product_manual':
            return sorted(self.product_manual_releases.keys())
        elif category == 'knowledge_base':
            return sorted(self.knowledge_base_releases.keys())
        else:
            # 返回所有
            all_releases = list(self.product_manual_releases.keys()) + list(self.knowledge_base_releases.keys())
            return sorted(all_releases)
    
    def get_all_releases_with_zips(self, category='product_manual'):
        """获取指定分类的所有release和zip文件的统一列表"""
        all_releases = []
        
        # 根据分类选择数据源
        if category == 'product_manual':
            releases = self.product_manual_releases
        elif category == 'knowledge_base':
            releases = self.knowledge_base_releases
        else:
            # 合并所有分类
            releases = {**self.product_manual_releases, **self.knowledge_base_releases}
        
        # 添加该分类的release目录
        for release_name in sorted(releases.keys()):
            all_releases.append({
                'name': release_name,
                'type': 'directory',
                'is_zip': False,
                'category': category,
                'doc_count': len(releases[release_name])
            })
        
        # 如果是product_manual，添加独立的zip文件
        if category == 'product_manual':
            for zip_name, zip_info in sorted(self.release_zips.items()):
                all_releases.append({
                    'name': zip_name,
                    'type': 'zip',
                    'is_zip': True,
                    'category': 'product_manual',
                    'size_human': zip_info['size_human'],
                    'zip_path': zip_info['path']
                })
        
        return all_releases
    
    def get_release_documents(self, release, category='product_manual'):
        """获取指定分类和release的所有文档"""
        if category == 'product_manual' and release in self.product_manual_releases:
            return sorted(self.product_manual_releases[release], key=lambda x: x['relative_in_release'])
        elif category == 'knowledge_base' and release in self.knowledge_base_releases:
            return sorted(self.knowledge_base_releases[release], key=lambda x: x['relative_in_release'])
        return []
    
    def search_documents(self, query):
        """搜索文档 - 支持分词搜索"""
        if not query or len(query.strip()) < 2:
            return []
        
        results = []
        query_terms = query.lower().split()  # 简单分词
        
        for doc in self.all_documents:
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
    
    def get_stats(self, category=None):
        """获取统计信息
        Args:
            category: 可选，指定分类 ('product_manual' 或 'knowledge_base')
                     如果为None，返回全局统计
        """
        # 根据分类过滤文档
        if category == 'product_manual':
            filtered_docs = [doc for doc in self.all_documents if doc.get('category') == 'product_manual']
            release_count = len(self.product_manual_releases)
        elif category == 'knowledge_base':
            filtered_docs = [doc for doc in self.all_documents if doc.get('category') == 'knowledge_base']
            release_count = len(self.knowledge_base_releases)
        else:
            # 全局统计
            filtered_docs = self.all_documents
            release_count = len(self.product_manual_releases) + len(self.knowledge_base_releases)
        
        # 计算文档总大小
        total_doc_size = sum(doc['size'] for doc in filtered_docs)
        
        # 按类型统计（基于过滤后的文档）
        type_stats = {}
        for doc in filtered_docs:
            doc_type = doc['type']
            if doc_type not in type_stats:
                type_stats[doc_type] = {'count': 0, 'size': 0}
            type_stats[doc_type]['count'] += 1
            type_stats[doc_type]['size'] += doc['size']
        
        # 按分类统计（全局数据，用于分类卡片显示）
        product_manual_docs = [doc for doc in self.all_documents if doc.get('category') == 'product_manual']
        knowledge_base_docs = [doc for doc in self.all_documents if doc.get('category') == 'knowledge_base']
        
        # 计算ZIP文件总大小（根据分类过滤）
        if category == 'product_manual':
            filtered_zips = {k: v for k, v in self.release_zips.items() 
                           if k in self.product_manual_releases}
        elif category == 'knowledge_base':
            filtered_zips = {k: v for k, v in self.release_zips.items() 
                           if k in self.knowledge_base_releases}
        else:
            filtered_zips = self.release_zips
            
        total_zip_size = sum(zip_info['size'] for zip_info in filtered_zips.values())
        
        return {
            'product_manual_count': len(self.product_manual_releases),
            'product_manual_doc_count': len(product_manual_docs),
            'knowledge_base_count': len(self.knowledge_base_releases),
            'knowledge_base_doc_count': len(knowledge_base_docs),
            'release_folders_count': release_count,
            'release_folders_doc_count': len(filtered_docs),
            'release_folders_total_size': total_doc_size,
            'release_folders_total_size_human': self.format_size(total_doc_size),
            'release_zips_count': len(filtered_zips),
            'release_zips_total_size': total_zip_size,
            'release_zips_total_size_human': self.format_size(total_zip_size),
            'type_stats': {k: {'count': v['count'], 'size_human': self.format_size(v['size'])} for k, v in type_stats.items()},
            # 保留原有字段以兼容现有代码
            'total_releases': release_count,
            'total_pdfs': sum(1 for doc in filtered_docs if doc['type'] == 'pdf'),
            'total_size': total_doc_size
        }

# 初始化文档管理器
doc_manager = None

@app.route('/')
def index():
    """主页 - 知识门户统一页面"""
    # 获取两个分类的数据
    pm_releases = doc_manager.get_all_releases_with_zips('product_manual')
    kb_releases = doc_manager.get_all_releases_with_zips('knowledge_base')
    
    # 获取两个分类的统计数据
    pm_stats = doc_manager.get_stats('product_manual')
    kb_stats = doc_manager.get_stats('knowledge_base')
    
    return render_template('portal.html', 
                         pm_releases=pm_releases, 
                         kb_releases=kb_releases,
                         pm_stats=pm_stats,
                         kb_stats=kb_stats)

@app.route('/knowledge-base')
def knowledge_base():
    """知识库页面 - 重定向到主页的知识库选项卡"""
    return redirect(url_for('index'), code=302)

@app.route('/product-manual')
def product_manual():
    """产品手册页面 - 重定向到主页的产品手册选项卡"""
    return redirect(url_for('index'), code=302)

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
                'size_human': doc['size_human'],
                'type': doc['type'],
                'category': doc.get('category', 'product_manual'),
                'absolute_path': doc.get('absolute_path', '')
            },
            'product': doc['release'],  # 使用release作为product
            'version': doc['release'],  # 使用release作为version
            'module': doc['relative_in_release'],  # 使用相对路径作为module
            'category': doc.get('category', 'product_manual')  # 添加分类信息
        }
        results.append(result)
    
    return jsonify(results)

@app.route('/release/<release>')
@app.route('/release/<category>/<release>')
def view_release(release, category='product_manual'):
    """查看release页面"""
    from urllib.parse import unquote
    
    # URL解码release名称以处理特殊字符
    decoded_release = unquote(release)
    
    # 首先检查是否是zip文件（只在product_manual分类中）
    if category == 'product_manual' and decoded_release in doc_manager.release_zips:
        zip_info = doc_manager.release_zips[decoded_release]
        return render_template('zip_notice.html', 
                             release=decoded_release, 
                             zip_info=zip_info,
                             category=category)
    
    # 正常的release目录
    documents = doc_manager.get_release_documents(decoded_release, category)
    if not documents:
        return "Release不存在", 404
    
    return render_template('release.html', release=decoded_release, documents=documents, category=category)

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

@app.route('/mhtml/<path:file_path>')
def view_mhtml(file_path):
    """查看MHTML文件"""
    
    # 构建完整路径
    full_path = doc_manager.base_path / file_path
    
    if not full_path.exists() or not full_path.is_file():
        return "文件不存在", 404
    
    # 检查文件类型
    if not str(full_path).lower().endswith(('.mhtml', '.mht')):
        return "不是MHTML文件", 400
    
    # MHTML文件可以直接作为HTML内容返回
    # 设置正确的MIME类型
    return send_file(
        str(full_path),
        mimetype='multipart/related',
        as_attachment=False
    )

@app.route('/archive/<path:file_path>')
def download_archive(file_path):
    """下载压缩包文件"""
    
    # 构建完整路径
    full_path = doc_manager.base_path / file_path
    
    if not full_path.exists() or not full_path.is_file():
        return "文件不存在", 404
    
    return send_file(str(full_path), as_attachment=True)

@app.route('/download/<path:file_path>')
def download_file(file_path):
    """下载文件"""
    
    full_path = doc_manager.base_path / file_path
    
    if not full_path.exists() or not full_path.is_file():
        return "文件不存在", 404
    
    return send_file(str(full_path), as_attachment=True)

@app.route('/test-mhtml')
def test_mhtml():
    """测试MHTML功能"""
    return render_template('test_mhtml.html')

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
    print(f"文档数量: {stats['release_folders_doc_count']}")
    if 'type_stats' in stats:
        for doc_type, type_info in stats['type_stats'].items():
            print(f"  - {doc_type.upper()}: {type_info['count']} 个 ({type_info['size_human']})")
    print(f"ZIP文件数量: {stats['release_zips_count']}")
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
