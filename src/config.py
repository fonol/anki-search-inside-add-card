import time
from aqt import mw
from functools import lru_cache


def _get_cache_key():
    return round(time.time() / 2)

@lru_cache()
def _get_config(cache_key):
    return mw.addonManager.getConfig(__name__)

def get_config_value(key):
    config = _get_config(_get_cache_key())
    try:
        return config[key]
    except KeyError:
        return None

def get_config_value_or_default(key, default):
    config = _get_config(_get_cache_key())
    try:
        if isinstance(key, str):
                return config[key]
        else:
            d = config
            for k in key:
                d = d[k]
            return d

    except KeyError:
        return default

