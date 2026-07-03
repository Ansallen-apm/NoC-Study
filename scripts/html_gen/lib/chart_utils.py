import json

def generate_chartjs_config(chart_id, type, data, options):
    config = {
        "type": type,
        "data": data,
        "options": options
    }
    return f"""
    const ctx_{chart_id} = document.getElementById('{chart_id}').getContext('2d');
    new Chart(ctx_{chart_id}, {json.dumps(config)});
    """
