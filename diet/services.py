import json
import re
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings


NEIS_MEAL_API_URL = 'https://open.neis.go.kr/hub/mealServiceDietInfo'
PROTEIN_PATTERN = re.compile(r'단백질\(g\)\s*([0-9.]+)')
ALLERGY_PATTERN = re.compile(r'\s*\([^)]*\)')


class SchoolMealConfigError(Exception):
    pass


def _clean_menu_name(name):
    return ALLERGY_PATTERN.sub('', name).strip()


def _extract_total_protein(nutrition_info):
    if not nutrition_info:
        return None

    match = PROTEIN_PATTERN.search(nutrition_info)
    if not match:
        return None

    return float(match.group(1))


def fetch_school_lunch(meal_date):
    if not settings.NEIS_API_KEY or not settings.NEIS_ATPT_CODE or not settings.NEIS_SCHOOL_CODE:
        raise SchoolMealConfigError('NEIS school lunch settings are not configured.')

    query = urlencode(
        {
            'KEY': settings.NEIS_API_KEY,
            'Type': 'json',
            'ATPT_OFCDC_SC_CODE': settings.NEIS_ATPT_CODE,
            'SD_SCHUL_CODE': settings.NEIS_SCHOOL_CODE,
            'MLSV_YMD': meal_date.strftime('%Y%m%d'),
        }
    )

    with urlopen(f'{NEIS_MEAL_API_URL}?{query}', timeout=10) as response:
        payload = json.loads(response.read().decode('utf-8'))

    if 'RESULT' in payload:
        code = payload['RESULT'].get('CODE')
        if code == 'INFO-200':
            return {
                'date': meal_date,
                'menus': [],
                'total_protein': None,
                'calories': None,
                'nutrition_info': '',
            }
        raise ValueError(payload['RESULT'].get('MESSAGE', 'Failed to fetch school lunch.'))

    meal_rows = payload.get('mealServiceDietInfo', [])
    if len(meal_rows) < 2 or 'row' not in meal_rows[1]:
        return {
            'date': meal_date,
            'menus': [],
            'total_protein': None,
            'calories': None,
            'nutrition_info': '',
        }

    meal = meal_rows[1]['row'][0]
    raw_menu = meal.get('DDISH_NM', '')
    menus = [
        {
            'name': _clean_menu_name(item),
            'protein_grams': None,
        }
        for item in raw_menu.split('<br/>')
        if _clean_menu_name(item)
    ]

    return {
        'date': meal_date,
        'menus': menus,
        'total_protein': _extract_total_protein(meal.get('NTR_INFO', '')),
        'calories': meal.get('CAL_INFO'),
        'nutrition_info': meal.get('NTR_INFO', ''),
    }
