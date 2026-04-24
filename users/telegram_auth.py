import hashlib
import hmac
import json
from time import time
from urllib.parse import parse_qsl


def validate_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> dict:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("initData hash topilmadi")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("initData imzosi noto'g'ri")

    auth_date = int(pairs.get("auth_date", "0"))
    if auth_date and time() - auth_date > max_age_seconds:
        raise ValueError("initData muddati tugagan")

    user_raw = pairs.get("user")
    if not user_raw:
        raise ValueError("initData user topilmadi")

    return json.loads(user_raw)
