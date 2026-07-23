import json
import os
import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from html_gen.lib.html_utils import render_template, save_html

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(ROOT_DIR, 'reports', 'cmn_dse')
DATA_FILE = os.path.join(REPORTS_DIR, 'data', 'data.json')
HTML_FILE = os.path.join(REPORTS_DIR, 'html', 'basic_CMN.html')

with open(DATA_FILE, 'r') as f:
    data = json.load(f)

html_content = render_template('basic_CMN.html',
                               base_path="../../../",
                               timestamp=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                               data=data,
                               chart_js=True,
                               datatables=False)

save_html(html_content, HTML_FILE)

print(f"HTML report successfully generated at: {HTML_FILE}")
