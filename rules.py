"""Validation rules applied to entity properties.

Rules are referenced by name from the configuration file. Each rule is a function
``(value, options) -> bool`` where ``value`` is the raw property value (a string, or
None when the property is absent) and ``options`` holds the remaining keys of the
check definition. Register a new rule by adding it to RULES.
"""
import re


def get_property(entity: dict, vocabulary_key: str, default=None) -> str:
    """Get a property from an entity.

    Args:
        entity (dict): Entity.
        vocabulary_key (str): Vocabulary key.
        default (str, optional): default value if property not found. Defaults to None.

    Returns:
        str: property value.
    """
    property_key = f'property-{vocabulary_key}'
    # properties are never None or empty
    if property_key in entity['properties']:
        return entity['properties'][property_key]
    return default


def validate_property(entity: dict, vocabulary_key: str, function: callable):
    """Validate a property of an entity.

    Args:
        entity (dict): Entity.
        vocabulary_key (str): Vocabulary key.
        function (callable): Validation function taking the property value.

    Returns:
        bool: True if property is valid, False otherwise.
    """
    return function(get_property(entity, vocabulary_key))


def cast_to_float(value: str, default: float = None) -> float:
    """Cast a string to float.

    Args:
        value (str): String to cast.
        default (float, optional): value returned when the cast fails.

    Returns:
        float: Float value, or `default` when the value is not a number.
    """
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# validation rules


def rule_present(value, options) -> bool:  # pylint: disable=unused-argument
    """Pass when the property exists and is not blank.

    Options:
        allow_blank (bool): count a whitespace-only value as present. Default False.
    """
    if value is None:
        return False
    if options.get('allow_blank', False):
        return True
    return str(value).strip() != ''


def rule_number(value, options) -> bool:
    """Pass when the value is numeric and inside the configured bounds.

    Options:
        min, max (float): inclusive bounds.
        exclusive_min, exclusive_max (float): exclusive bounds.
    """
    number = cast_to_float(value)
    if number is None:
        return False
    for option, comparison in (
            ('min', lambda n, b: n >= b),
            ('max', lambda n, b: n <= b),
            ('exclusive_min', lambda n, b: n > b),
            ('exclusive_max', lambda n, b: n < b)):
        bound = options.get(option)
        if bound is not None and not comparison(number, float(bound)):
            return False
    return True


def rule_latitude(value, options) -> bool:
    """Pass when the value is a latitude between -90 and 90."""
    return rule_number(value, {'min': -90, 'max': 90, **options})


def rule_longitude(value, options) -> bool:
    """Pass when the value is a longitude between -180 and 180."""
    return rule_number(value, {'min': -180, 'max': 180, **options})


def rule_allowed_values(value, options) -> bool:
    """Pass when the value is one of an explicit list.

    Options:
        values (list): the accepted values. Required.
        case_sensitive (bool): default True.
    """
    values = options.get('values', [])
    if value is None:
        return False
    if options.get('case_sensitive', True):
        return value in values
    return str(value).casefold() in {str(v).casefold() for v in values}


def rule_regex(value, options) -> bool:
    """Pass when the value matches a regular expression.

    Options:
        pattern (str): the expression, anchored with fullmatch. Required.
        ignore_case (bool): default False.
    """
    pattern = options.get('pattern')
    if value is None or pattern is None:
        return False
    flags = re.IGNORECASE if options.get('ignore_case', False) else 0
    return re.fullmatch(pattern, str(value), flags) is not None


def rule_length(value, options) -> bool:
    """Pass when the value's length is inside the configured bounds.

    Options:
        min, max (int): inclusive bounds on the string length.
    """
    if value is None:
        return False
    length = len(str(value))
    minimum, maximum = options.get('min'), options.get('max')
    if minimum is not None and length < int(minimum):
        return False
    if maximum is not None and length > int(maximum):
        return False
    return True


def rule_equal(values, options) -> bool:
    """Pass when every key of a multi-key check holds the same value.

    Options:
        case_sensitive (bool): default True.
        ignore_missing (bool): pass when every key is absent. Default False.
    """
    if all(value is None for value in values):
        return options.get('ignore_missing', False)
    if options.get('case_sensitive', True):
        compared = [None if v is None else str(v) for v in values]
    else:
        compared = [None if v is None else str(v).casefold() for v in values]
    return len(set(compared)) == 1


def rule_in_reference_set(value, options) -> bool:
    """Pass when the value appears in a named reference set.

    Options:
        reference_set (str): name of the set. Required.
        case_sensitive (bool): default True.
    """
    reference_set = options.get('_resolved_reference_set', set())
    if value is None:
        return False
    if options.get('case_sensitive', True):
        return value in reference_set
    return str(value).casefold() in {str(v).casefold() for v in reference_set}


# Rules that receive every key's value at once rather than one value per key.
MULTI_VALUE_RULES = {'equal'}

RULES = {
    'present': rule_present,
    'number': rule_number,
    'latitude': rule_latitude,
    'longitude': rule_longitude,
    'allowed_values': rule_allowed_values,
    'regex': rule_regex,
    'length': rule_length,
    'equal': rule_equal,
    'in_reference_set': rule_in_reference_set,
}


def get_rule(name: str) -> callable:
    """Look up a rule by its configured name.

    Args:
        name (str): rule name.

    Returns:
        callable: the rule function.

    Raises:
        KeyError: when the rule is not registered.
    """
    if name not in RULES:
        raise KeyError(
            f'Unknown rule "{name}". Available rules: {", ".join(sorted(RULES))}.')
    return RULES[name]
