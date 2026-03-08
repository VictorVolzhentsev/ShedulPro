import urllib.parse
import re
import datetime

# Yekaterinburg timezone (UTC+5)
YEKT = datetime.timezone(datetime.timedelta(hours=5))

def get_yekt_datetime() -> datetime.datetime:
    """Returns the current aware datetime in Yekaterinburg (UTC+5) timezone."""
    return datetime.datetime.now(YEKT)

def get_yekt_date() -> datetime.date:
    """Returns the current date in Yekaterinburg timezone."""
    return get_yekt_datetime().date()

def generate_map_link(location_text: str) -> str:
    """
    Generates a Yandex Maps link for a given location text.
    If the text is already a URL, returns it as is.
    Otherwise, creates a search link.
    """
    if not location_text:
        return ""
        
    text = location_text.strip()
    if not text:
        return ""
        
    # If it's already a link, return it
    if text.startswith('http://') or text.startswith('https://'):
        return text
        
    # Clean the text: remove anything in parentheses, e.g., "(гибридный формат)"
    cleaned_text = re.sub(r'\(.*?\)', '', text).strip()
    
    # Ensure it searches in Yekaterinburg to avoid finding streets in other cities
    search_query = f"Екатеринбург, {cleaned_text}"

    # Construct Yandex Maps search link
    # https://yandex.ru/maps/?text=<encoded_text>
    encoded_text = urllib.parse.quote(search_query)
    return f"https://yandex.ru/maps/?text={encoded_text}"
