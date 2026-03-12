# ifitwala_ed/assessment/check_flags.py

from __future__ import annotations

FALSE_CHECK_VALUES = {"", "0", "false", "no", "off"}
TRUE_CHECK_VALUES = {"1", "true", "yes", "on"}


def is_checked(value: object) -> bool:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in FALSE_CHECK_VALUES:
            return False
        if normalized in TRUE_CHECK_VALUES:
            return True
        return bool(normalized)

    return bool(value)


def to_check_value(value: object) -> int:
    return 1 if is_checked(value) else 0
