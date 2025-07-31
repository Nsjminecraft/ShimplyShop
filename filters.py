from datetime import datetime
from flask import current_app

def init_app(app):
    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%b %d, %Y'):
        if not value:
            return ''
        try:
            # If it's already a datetime object, format it
            if hasattr(value, 'strftime'):
                return value.strftime(format)
            
            # If it's a string, try to parse it
            if isinstance(value, str):
                # Try ISO format first
                try:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return dt.strftime(format)
                except ValueError:
                    # Try other common formats if ISO fails
                    for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            dt = datetime.strptime(value, fmt)
                            return dt.strftime(format)
                        except ValueError:
                            continue
            
            # If we get here, we couldn't parse the date
            current_app.logger.warning(f'Could not parse date: {value}')
            return str(value)
            
        except Exception as e:
            current_app.logger.error(f'Error formatting date {value}: {str(e)}')
            return str(value)
