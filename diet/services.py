import json
import re
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings


NEIS_MEAL_API_URL = 'https://open.neis.go.kr/hub/mealServiceDietInfo'
PROTEIN_PATTERN = re.compile('\ub2e8\ubc31\uc9c8\\(g\\)\\s*([0-9.]+)')
ALLERGY_PATTERN = re.compile(r'\s*\([^)]*\)')
MEAL_TYPE_CODES = {
    'breakfast': '1',
    'lunch': '2',
    'dinner': '3',
}
MEAL_TYPE_LABELS = {
    'breakfast': 'Breakfast',
    'lunch': 'Lunch',
    'dinner': 'Dinner',
}
PORTION_MULTIPLIERS = {
    'none': 0.0,
    'small': 0.5,
    'medium': 1.0,
    'large': 1.5,
}
PROTEIN_KEYWORD_ESTIMATES = [
    ('\ub2ed\uac08\ube44', 12.0),
    ('\uce58\ud0a8\ub108\uac9f', 11.0),
    ('\ub108\uac9f', 11.0),
    ('\uce58\ud0a8\ud150\ub354', 12.0),
    ('\ud150\ub354', 12.0),
    ('\uce58\ud0a8\uac00\ub77c\uc544\uac8c', 12.0),
    ('\uac00\ub77c\uc544\uac8c', 12.0),
    ('\ud6c4\ub77c\uc774\ub4dc', 12.0),
    ('\uce58\ud0a8', 12.0),
    ('\ub2ed', 12.0),
    ('\ub2ed\ubd09', 11.0),
    ('\ud1b5\uc0b4', 12.0),
    ('\uacc4\ub780', 6.0),
    ('\ub2ec\uac40', 6.0),
    ('\uba54\ucd94\ub9ac\uc54c', 5.0),
    ('\ub450\ubd80', 8.0),
    ('\ub450\uc720', 5.0),
    ('\ucf69', 7.0),
    ('\ub3c8\uc721', 11.0),
    ('\ub3fc\uc9c0', 11.0),
    ('\uc81c\uc721', 11.0),
    ('\ub3c8\uac08\ube44', 12.0),
    ('\ub5a1\uac08\ube44', 11.0),
    ('\ub3d9\uadf8\ub791\ub561', 9.0),
    ('\ubbf8\ud2b8\ubcfc', 10.0),
    ('\uc644\uc790', 9.0),
    ('\uc18c\uace0\uae30', 12.0),
    ('\ubd88\uace0\uae30', 12.0),
    ('\ud06c\ud150', 12.0),
    ('\uc2a4\ud15c', 12.0),
    ('\ud584', 7.0),
    ('\uc18c\uc2dc\uc9c0', 7.0),
    ('\ube44\uc5d4\ub098', 7.0),
    ('\uc2a4\ud338', 7.0),
    ('\ubca0\uc774\ucee8', 7.0),
    ('\ucc38\uce58', 10.0),
    ('\uc7a5\uc5b4', 11.0),
    ('\uace0\ub4f1\uc5b4', 11.0),
    ('\uc0bc\uce58', 11.0),
    ('\uaf2c\uce58', 10.0),
    ('\uace0\ub4f1\uc5b4', 11.0),
    ('\uc5f0\uc5b4', 11.0),
    ('\uc0dd\uc120', 10.0),
    ('\uc5b4\ubb35', 7.0),
    ('\uc624\uc9d5\uc5b4', 10.0),
    ('\uc0c8\uc6b0', 9.0),
    ('\uc870\uac1c', 9.0),
    ('\uad74', 9.0),
    ('\uba39\ud0dc', 10.0),
    ('\uba85\ud0dc', 10.0),
    ('\ucf54\ub2e4\ub9ac', 10.0),
    ('\uce58\uc988', 6.0),
    ('\ub9ac\ucf54\ud0c0', 6.0),
    ('\uc6b0\uc720', 6.0),
    ('\uc694\uac70\ud2b8', 5.0),
    ('\uadf8\ub9ad\uc694\uac70\ud2b8', 8.0),
]
EXCLUDED_MENU_KEYWORDS = [
    '\ubc25',
    '\uc7a1\uace1\ubc25',
    '\ub204\ub8fd\uc9c0',
    '\uc8fd',
    '\ube75',
    '\uba74',
    '\uad6d',
    '\ud0d5',
    '\ucc0c\uac1c',
    '\uae40\uce58',
    '\ub098\ubb3c',
    '\ubb34\uce68',
    '\uc0d0\ub7ec\ub4dc',
    '\uacfc\uc77c',
    '\uc74c\ub8cc',
    '\uc8fc\uc2a4',
]


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


def _estimate_menu_protein_grams(menu_name):
    matched_values = [grams for keyword, grams in PROTEIN_KEYWORD_ESTIMATES if keyword in menu_name]
    if matched_values:
        return max(matched_values)

    if any(keyword in menu_name for keyword in EXCLUDED_MENU_KEYWORDS):
        return None

    return None


def _build_selection_options(base_grams):
    return {
        key: round(base_grams * multiplier, 1)
        for key, multiplier in PORTION_MULTIPLIERS.items()
    }


def transform_school_meal_for_app(school_meal, meal_type):
    items = []
    total_estimated_protein = 0.0

    for menu in school_meal['menus']:
        estimated_protein = _estimate_menu_protein_grams(menu['name'])
        if estimated_protein is None:
            continue

        total_estimated_protein += estimated_protein
        items.append(
            {
                'name': menu['name'],
                'estimated_protein_grams': round(estimated_protein, 1),
                'selection_options': _build_selection_options(estimated_protein),
                'default_selection': 'none',
            }
        )

    return {
        'date': school_meal['date'],
        'meal_type': meal_type,
        'meal_type_label': MEAL_TYPE_LABELS[meal_type],
        'menus': items,
        'estimated_total_protein': round(total_estimated_protein, 1),
        'school_total_protein': school_meal['total_protein'],
        'calories': school_meal['calories'],
        'nutrition_info': school_meal['nutrition_info'],
    }


def fetch_school_lunch(meal_date, meal_type='lunch'):
    if not settings.NEIS_API_KEY or not settings.NEIS_ATPT_CODE or not settings.NEIS_SCHOOL_CODE:
        raise SchoolMealConfigError('NEIS school lunch settings are not configured.')
    if meal_type not in MEAL_TYPE_CODES:
        raise ValueError('meal_type must be one of breakfast, lunch, dinner.')

    query = urlencode(
        {
            'KEY': settings.NEIS_API_KEY,
            'Type': 'json',
            'ATPT_OFCDC_SC_CODE': settings.NEIS_ATPT_CODE,
            'SD_SCHUL_CODE': settings.NEIS_SCHOOL_CODE,
            'MLSV_YMD': meal_date.strftime('%Y%m%d'),
            'MMEAL_SC_CODE': MEAL_TYPE_CODES[meal_type],
        }
    )

    with urlopen(f'{NEIS_MEAL_API_URL}?{query}', timeout=10) as response:
        payload = json.loads(response.read().decode('utf-8'))

    if 'RESULT' in payload:
        code = payload['RESULT'].get('CODE')
        if code == 'INFO-200':
            return {
                'date': meal_date,
                'meal_type': meal_type,
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
            'meal_type': meal_type,
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
        'meal_type': meal_type,
        'menus': menus,
        'total_protein': _extract_total_protein(meal.get('NTR_INFO', '')),
        'calories': meal.get('CAL_INFO'),
        'nutrition_info': meal.get('NTR_INFO', ''),
    }
