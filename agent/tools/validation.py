"""Validador ligero de argumentos de tools contra un subconjunto de JSON Schema."""

# Tipos JSON Schema soportados y su equivalente en Python. Cubre lo que usan
# hoy las tools del proyecto; si en el futuro hace falta "null" u otros tipos,
# se amplia aqui.
_TYPE_MAP = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "array": list,
    "object": dict,
}


class ToolValidationError(ValueError):
    """Los argumentos de una tool no cumplen su JSON Schema."""


def validate_args(schema: dict, args: dict) -> None:
    """Valida un diccionario de argumentos contra el JSON Schema de una tool.

    Cubre el subconjunto de JSON Schema usado por las tools del proyecto:
    "properties", "required", "enum" por propiedad y "additionalProperties".
    No valida schemas anidados (objetos u arrays dentro de propiedades); las
    tools actuales no los usan.

    Args:
        schema: JSON Schema de los argumentos, en el mismo formato que
            ToolSpec.parameters (ver agent/tools/spec.py), p. ej.
            {"type": "object", "properties": {...}, "required": [...]}.
        args: Argumentos ya parseados (de json.loads) a validar.

    Raises:
        ToolValidationError: Si `args` no es un objeto, falta un argumento
            requerido, aparece un argumento no declarado en "properties" y
            "additionalProperties" no es True, un valor no coincide con el
            "type" declarado, o un valor no esta en su "enum".
    """
    if not isinstance(args, dict):
        raise ToolValidationError("los argumentos deben ser un objeto JSON")

    properties = schema.get("properties", {})
    required = schema.get("required", [])
    allow_extra = schema.get("additionalProperties", False)

    for key in required:
        if key not in args:
            raise ToolValidationError(f"falta el argumento requerido '{key}'")

    for key, value in args.items():
        if key not in properties:
            if allow_extra:
                continue
            raise ToolValidationError(f"argumento no permitido '{key}'")

        prop_schema = properties[key]
        expected_type = prop_schema.get("type")
        if expected_type in _TYPE_MAP:
            py_type = _TYPE_MAP[expected_type]
            if expected_type == "integer" and isinstance(value, bool):
                raise ToolValidationError(f"'{key}' debe ser integer, no boolean")
            if not isinstance(value, py_type):
                raise ToolValidationError(f"'{key}' debe ser de tipo {expected_type}")

        enum = prop_schema.get("enum")
        if enum is not None and value not in enum:
            raise ToolValidationError(f"'{key}' debe ser uno de {enum}")


if __name__ == "__main__":
    _SCHEMA = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "modo": {"type": "string", "enum": ["a", "b"]},
        },
        "required": ["path"],
    }

    validate_args(_SCHEMA, {"path": "x.txt"})

    try:
        validate_args(_SCHEMA, {})
        raise AssertionError("deberia fallar por falta de 'path'")
    except ToolValidationError:
        pass

    try:
        validate_args(_SCHEMA, {"path": 123})
        raise AssertionError("deberia fallar por tipo incorrecto")
    except ToolValidationError:
        pass

    try:
        validate_args(_SCHEMA, {"path": "x.txt", "extra": "y"})
        raise AssertionError("deberia fallar por argumento no declarado")
    except ToolValidationError:
        pass

    try:
        validate_args(_SCHEMA, {"path": "x.txt", "modo": "z"})
        raise AssertionError("deberia fallar por valor fuera de enum")
    except ToolValidationError:
        pass

    print("OK: agent/tools/validation.py autochequeo pasado")
