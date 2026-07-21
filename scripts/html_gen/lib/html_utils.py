import os
import jinja2
import shutil

def get_jinja_env():
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

def render_template(template_name, **kwargs):
    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(**kwargs)

def sync_root_assets():
    """Syncs the static directory and index.html to the root of the repo so reports can be viewed directly."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    source_static = os.path.join(base_dir, 'scripts', 'html_gen', 'static')
    dest_static = os.path.join(base_dir, 'static')

    if os.path.exists(dest_static):
        shutil.rmtree(dest_static)
    shutil.copytree(source_static, dest_static)

    # Generate root index.html
    index_html = render_template('index.html', base_path="./", datatables=False, chart_js=False)
    with open(os.path.join(base_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)

def save_html(html_content, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Auto-sync root assets to ensure local repo viewing works seamlessly
    sync_root_assets()
