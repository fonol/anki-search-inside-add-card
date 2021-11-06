# anki-search-inside-add-card
# Copyright (C) 2019 - 2021 Tom Z.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
    except (KeyError, TypeError):
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


def update_config(key, value):
    config = _get_config(_get_cache_key())
    config[key] = value
    mw.addonManager.writeConfig(__name__, config)
