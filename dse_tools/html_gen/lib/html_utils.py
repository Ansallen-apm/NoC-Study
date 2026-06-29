def generate_html_document(title, css_styles, body_content, scripts=""):
    """
    Generates the outer HTML document structure.
    """
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; color: #333; }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            {css_styles}
        </style>
    </head>
    <body>
        <div class="container">
            {body_content}
        </div>
        {scripts}
    </body>
    </html>
    """
