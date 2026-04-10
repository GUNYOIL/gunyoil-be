import base64
import json
import os


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
