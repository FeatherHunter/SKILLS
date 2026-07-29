"""
lib.intent_v3_validator — intent.json v3.0 协议校验器

加载 references/intent_v3.schema.json,提供 validate_intent 函数。
失败返回 (False, 错误列表);成功返回 (True, [])。

使用方式:
    from intent_v3_validator import validate_intent, SCHEMA_PATH

    valid, errors = validate_intent(intent_dict)
    if not valid:
        for path, msg in errors:
            print(f"{path}: {msg}")
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import jsonschema
except ImportError:
    raise ImportError(
        "jsonschema is required for intent_v3_validator. "
        "pip install 'jsonschema>=4.0'"
    )


# Schema 路径(从 lib/ 回到仓库根)
SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SKILL_ROOT / "references" / "intent_v3.schema.json"


def _load_schema() -> Dict:
    """加载 v3.0 schema。带缓存。"""
    if not hasattr(_load_schema, "_cache"):
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            _load_schema._cache = json.load(f)
    return _load_schema._cache


def validate_intent(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """校验 intent.json 是否符合 v3.0 spec。

    Args:
        data: 已解析的 intent.json dict

    Returns:
        (is_valid, error_list)
        - is_valid: True = 通过校验,False = 有错误
        - error_list: 错误信息列表,每项格式为 "{field_path}: {message}"
    """
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    formatted = []
    for err in errors:
        path = "/".join(str(p) for p in err.path) or "<root>"
        formatted.append(f"{path}: {err.message}")

    return len(errors) == 0, formatted


def clear_cache() -> None:
    """清空 schema 缓存(测试用)。"""
    if hasattr(_load_schema, "_cache"):
        del _load_schema._cache