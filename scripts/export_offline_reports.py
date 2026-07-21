import os
import shutil
import zipfile

def export_offline():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(base_dir, 'reports')
    bundle_dir = os.path.join(base_dir, 'offline_bundle')
    static_dir = os.path.join(base_dir, 'scripts', 'html_gen', 'static')
    templates_dir = os.path.join(base_dir, 'scripts', 'html_gen', 'templates')

    if os.path.exists(bundle_dir):
        shutil.rmtree(bundle_dir)
    os.makedirs(bundle_dir)

    # 1. Copy reports structure and HTML files
    # We only want to copy html directories and their contents.
    # The JSON data is embedded in the HTML files, so we don't need the 'data' directories.
    # Note: we also want to render the index.html from templates

    for report_topic in os.listdir(reports_dir):
        topic_path = os.path.join(reports_dir, report_topic)
        if os.path.isdir(topic_path):
            html_path = os.path.join(topic_path, 'html')
            if os.path.exists(html_path):
                dest_topic_path = os.path.join(bundle_dir, 'reports', report_topic, 'html')
                os.makedirs(dest_topic_path, exist_ok=True)
                for item in os.listdir(html_path):
                    if item.endswith('.html'):
                        shutil.copy2(os.path.join(html_path, item), dest_topic_path)

    # 2. & 3. Sync static assets and render dynamic index.html
    sys.path.insert(0, base_dir)
    from scripts.html_gen.lib.html_utils import sync_root_assets

    sync_root_assets(bundle_dir)

    # 4. Zip the bundle
    zip_path = os.path.join(base_dir, 'offline_bundle.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(bundle_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, bundle_dir)
                zipf.write(file_path, arcname)

    print(f"Offline bundle generated at {bundle_dir} and zipped to {zip_path}")

if __name__ == "__main__":
    import sys
    export_offline()
