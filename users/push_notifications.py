import base64
import json
import os

from django.utils import timezone


def _decode_base64(encoded_value):
    try:
        return base64.b64decode(encoded_value).decode('utf-8')
    except Exception:
        return base64.urlsafe_b64decode(encoded_value).decode('utf-8')


def _load_service_account_json():
    service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
    service_account_json_base64 = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON_BASE64')
    if service_account_json_base64:
        return _decode_base64(service_account_json_base64)

    if service_account_json:
        return service_account_json

    base64_parts = []
    prefix = 'FIREBASE_SERVICE_ACCOUNT_JSON_BASE64_PART_'
    for key, value in os.environ.items():
        if key.startswith(prefix):
            try:
                index = int(key.removeprefix(prefix))
            except ValueError:
                continue
            base64_parts.append((index, value))

    if base64_parts:
        ordered = ''.join(value for _, value in sorted(base64_parts))
        return _decode_base64(ordered)

    raise RuntimeError(
        'FIREBASE_SERVICE_ACCOUNT_JSON, FIREBASE_SERVICE_ACCOUNT_JSON_BASE64, '
        'or FIREBASE_SERVICE_ACCOUNT_JSON_BASE64_PART_* is not configured.'
    )


def _load_firebase_admin():
    import firebase_admin
    from firebase_admin import credentials, messaging

    if not firebase_admin._apps:
        service_account_json = _load_service_account_json()
        credentials_info = json.loads(service_account_json)
        firebase_admin.initialize_app(credentials.Certificate(credentials_info))

    return messaging


def send_push_notification(token, title, body, data=None):
    messaging = _load_firebase_admin()
    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
    )
    return messaging.send(message)


def send_push_notifications(tokens, title, body, data=None):
    results = []
    for token in tokens:
        try:
            message_id = send_push_notification(token=token, title=title, body=body, data=data)
            results.append({'token': token, 'success': True, 'message_id': message_id})
        except Exception as exc:
            results.append({'token': token, 'success': False, 'error': str(exc)})
    return results


def get_lunch_reminder_targets(target_date=None):
    from diet.models import SchoolMealSelectionLog
    from users.models import UserPushToken

    if target_date is None:
        target_date = timezone.localdate()

    lunch_logged_user_ids = set(
        SchoolMealSelectionLog.objects.filter(date=target_date, meal_type='lunch').values_list('user_id', flat=True)
    )

    active_tokens = UserPushToken.objects.filter(is_active=True).select_related('user').order_by('-updated_at', '-id')
    targets = []
    for push_token in active_tokens:
        if push_token.user_id in lunch_logged_user_ids:
            continue
        targets.append(push_token)
    return targets


def send_lunch_reminders(target_date=None):
    if target_date is None:
        target_date = timezone.localdate()

    title = os.getenv('PUSH_LUNCH_TITLE', '점심 급식을 기록해보세요!')
    body = os.getenv('PUSH_LUNCH_BODY', title)
    targets = get_lunch_reminder_targets(target_date=target_date)
    results = send_push_notifications(
        [target.token for target in targets],
        title=title,
        body=body,
        data={'type': 'lunch-reminder', 'date': target_date.isoformat()},
    )

    invalid_errors = {'Device unregistered.', 'NotRegistered'}
    invalid_tokens = [result['token'] for result in results if not result['success'] and result.get('error') in invalid_errors]
    if invalid_tokens:
        from users.models import UserPushToken

        UserPushToken.objects.filter(token__in=invalid_tokens).update(is_active=False)

    return {
        'date': target_date.isoformat(),
        'target_count': len(targets),
        'success_count': sum(1 for result in results if result['success']),
        'failure_count': sum(1 for result in results if not result['success']),
        'results': results,
    }
