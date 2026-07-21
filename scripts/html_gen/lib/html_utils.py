import os
import jinja2

def get_jinja_env():
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

def render_template(template_name, **kwargs):
    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(**kwargs)

def save_html(html_content, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

def create_html_scaffold(title, content, js_data_str="", chart_js=True, datatables=False):
    # This is a legacy function for scripts not yet migrated to Jinja2
    scripts = ""
    if chart_js:
        scripts += '<script src="../../static/js/chart.js"></script>\n'
    if datatables:
        scripts += '<link rel="stylesheet" type="text/css" href="../../static/css/jquery.dataTables.css">\n'
        scripts += '<script type="text/javascript" charset="utf8" src="../../static/js/jquery.js"></script>\n'
        scripts += '<script type="text/javascript" charset="utf8" src="../../static/js/jquery.dataTables.js"></script>\n'

    js_section = f"<script>{js_data_str}</script>" if js_data_str else ""

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-width=1.0">
    <title>{title}</title>
    {scripts}
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: center; }}
        th {{ background-color: #34495e; color: white; }}
        .chart-container {{ background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        {content}
    </div>
    {js_section}
</body>
</html>"""
    return html
