import os
import jinja2

def get_jinja_env():
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

def render_template(template_name, **kwargs):
    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(**kwargs)

import shutil

REPORT_META_MAP = {
    'unified_dashboard.html': ('整合儀表板 (Unified Dashboard)', '提供綜合性的指標與效能總覽。'),
    'interactive_dse_trends.html': ('交叉驗證 DSE (Interactive DSE)', '互動式架構探索與多項參數 (Topology, VCs, Buffers) 影響分析。'),
    'full_ring_dse_comparison.html': ('Ring 拓撲報告 (Ring DSE)', '針對 Ring 拓撲在不同條件下的理論與實際效能報告。'),
    'advanced_micro_metrics_report.html': ('微觀指標報告 (Micro Metrics)', 'Queueing Theory 與微觀緩衝區狀態的進階分析。'),
    'multi_model_cmp.html': ('多模型比較 (Multi-Model Cmp)', '比較不同層級模擬模型 (C-model vs. BookSim 等) 的準確度與效能差異。'),
    'custom_workload_report.html': ('自訂工作負載 (Custom Workload)', '特定自訂 Traffic Pattern 下的網路效能報告。'),
    'ca_visualizer.html': ('華為 CA 視覺化 (CA Visualizer)', 'Cycle-Accurate 視覺化工具，用於查看封包流動狀態。'),
    'basic_CMN.html': ('CMN DSE (CMN Dashboard)', '針對 CMN 相關架構的探索報告。')
}

def sync_root_assets(dest_dir):
    """
    Syncs static assets to dest_dir/static and dynamically generates dest_dir/index.html
    by scanning the dest_dir/reports directory for available HTML files.
    """
    # 1. Sync static directory
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_static = os.path.join(script_dir, 'static')
    dest_static = os.path.join(dest_dir, 'static')

    if os.path.exists(dest_static):
        shutil.rmtree(dest_static)
    if os.path.exists(src_static):
        shutil.copytree(src_static, dest_static)

    # 2. Dynamically scan reports directory
    reports_dir = os.path.join(dest_dir, 'reports')
    available_reports = []

    if os.path.exists(reports_dir):
        for topic in os.listdir(reports_dir):
            topic_path = os.path.join(reports_dir, topic)
            if os.path.isdir(topic_path):
                html_dir = os.path.join(topic_path, 'html')
                if os.path.exists(html_dir) and os.path.isdir(html_dir):
                    for filename in os.listdir(html_dir):
                        if filename.endswith('.html'):
                            meta = REPORT_META_MAP.get(filename, (filename, 'No description available.'))
                            rel_path = f"reports/{topic}/html/{filename}"
                            available_reports.append({
                                'path': rel_path,
                                'title': meta[0],
                                'desc': meta[1]
                            })

    # Sort for consistent ordering
    available_reports.sort(key=lambda x: x['title'])

    # 3. Define related manual docs
    related_docs = [
        {
            'path': 'huawei_c_model/architecture.html',
            'title': '架構設計文件 (Architecture)',
            'desc': 'Huawei CA 模型的軟體與微架構設計說明。'
        },
        {
            'path': 'huawei_c_model/ca_verify_trace_viewer.html',
            'title': 'CA Trace 逐拍檢視器 (Trace Viewer)',
            'desc': 'ca_verify_3x3 情境的 cycle-by-cycle trace 檢視與預期行為敘述。'
        }
    ]

    # 4. Render and save index.html
    index_html_content = render_template('index.html', base_path='./', datatables=False, chart_js=False, reports=available_reports, related_docs=related_docs)
    index_path = os.path.join(dest_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_html_content)

def save_html(html_content, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Auto-sync root assets (repo root is 4 levels up from a report file like reports/cmn_dse/html/basic_CMN.html)
    # But just to be robust, find the repo root.
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(filepath)))))
    # Double check it is the repo root by looking for 'reports'
    if os.path.exists(os.path.join(repo_root, 'reports')) or os.path.basename(repo_root) == 'offline_bundle':
         sync_root_assets(repo_root)
    elif 'reports' in filepath:
        # Fallback to finding 'reports' in the path
        parts = filepath.split(os.sep)
        try:
            reports_index = parts.index('reports')
            repo_root = os.sep.join(parts[:reports_index])
            if repo_root == "":
                repo_root = "."
            sync_root_assets(repo_root)
        except ValueError:
            pass
