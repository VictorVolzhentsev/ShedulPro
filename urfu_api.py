import aiohttp
import datetime
import logging
import utils

BASE_URL = "https://urfu.ru/api/v2/schedule"

# S2: Request timeout to prevent hanging
_TIMEOUT = aiohttp.ClientTimeout(total=15)

# A2: Reuse aiohttp session across requests
_session: aiohttp.ClientSession | None = None


def _get_session() -> aiohttp.ClientSession:
    """Returns a shared aiohttp session, creating one if needed."""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=_TIMEOUT)
    return _session


async def search_group(query):
    url = f"{BASE_URL}/groups"
    params = {"search": query}

    logging.info(f"Searching group: {url} with params {params}")

    try:
        session = _get_session()
        async with session.get(url, params=params) as response:
            logging.info(f"Search response status: {response.status}")
            if response.status == 200:
                data = await response.json()
                logging.info(f"Found {len(data)} groups")
                return data
            return []
    except aiohttp.ClientError as e:
        logging.error(f"HTTP error searching groups: {e}")
        return []


async def get_schedule(group_id, date_start=None, date_end=None):
    if not date_start:
        date_start = utils.get_yekt_date().strftime("%Y-%m-%d")
    if not date_end:
        today = utils.get_yekt_date()
        days_ahead = 7 - today.weekday() + 7
        date_end = (today + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/groups/{group_id}/schedule"
    params = {
        "date_gte": date_start,
        "date_lte": date_end
    }

    logging.info(f"Requesting schedule: {url} with params {params}")

    try:
        session = _get_session()
        async with session.get(url, params=params) as response:
            logging.info(f"Schedule response status: {response.status}")
            if response.status == 200:
                data = await response.json()
                events_count = len(data.get('events', []))
                logging.info(f"Received {events_count} events")
                if events_count == 0:
                    logging.info(f"Full response for empty schedule: {data}")
                return data
            else:
                logging.error(f"Error requesting schedule: {await response.text()}")
            return None
    except aiohttp.ClientError as e:
        logging.error(f"HTTP error requesting schedule: {e}")
        return None


async def close_session():
    """Closes the active client session."""
    global _session
    if _session and not _session.closed:
        await _session.close()

