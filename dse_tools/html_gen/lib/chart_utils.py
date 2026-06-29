import json

def generate_chartjs_config(chart_type, labels, datasets, options=None):
    """
    Generates a generic Chart.js configuration dictionary.
    """
    if options is None:
        options = {}

    return {
        'type': chart_type,
        'data': {
            'labels': labels,
            'datasets': datasets
        },
        'options': options
    }

def get_base_options(title_text, x_title, y_title):
    return {
        'responsive': True,
        'maintainAspectRatio': False,
        'plugins': {
            'title': {
                'display': True,
                'text': title_text,
                'font': {'size': 18}
            },
            'tooltip': {
                'mode': 'index',
                'intersect': False,
            },
        },
        'scales': {
            'x': {
                'title': {
                    'display': True,
                    'text': x_title
                }
            },
            'y': {
                'title': {
                    'display': True,
                    'text': y_title
                },
                'beginAtZero': True
            }
        }
    }
