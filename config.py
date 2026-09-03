"""Load and validate the metrics configuration.

Every customer-specific input -- entity types, vocabulary keys, validation rules,
reference sets and the target table layout -- lives in a JSON configuration file so
that this repository contains no customer data. See README.md for the full reference.
"""
import json
import os
import re

DEFAULT_CONFIG_PATH = 'config/metrics.json'

# Dimensions whose checks do not need an explicit `rule`.
DEFAULT_RULES = {
    'completeness': 'present',
    'uniqueness': 'unique',
}

# Value substituted for a missing property when building a composite metric key.
DEFAULT_MISSING_VALUE = 'N/A'

DEFAULT_COLUMNS = {
    'id': 'GDQMId',
    'name': 'MetricName',
    'value': 'MetricValue',
    'info': 'MetricInfo',
    'created_date': 'DWCreatedDate',
    'created_by': 'DWCreatedBy',
    'modified_date': 'DWModifiedDate',
    'modified_by': 'DWModifiedBy',
}

# A SQL identifier part: no brackets, no separators, no empty strings.
_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_@$#]*$')


class ConfigError(Exception):
    """Raised when the configuration file is missing or invalid."""


def _require(condition: bool, message: str):
    """Raise a ConfigError when a configuration expectation is not met.

    Args:
        condition (bool): expectation that must hold.
        message (str): message to report when it does not.
    """
    if not condition:
        raise ConfigError(message)


def validate_identifier(name: str, what: str) -> str:
    """Validate a SQL identifier, which is interpolated rather than parameterised.

    Args:
        name (str): identifier, optionally dotted (``schema.Table``).
        what (str): description used in the error message.

    Returns:
        str: the identifier, bracket-quoted part by part.
    """
    _require(isinstance(name, str) and name.strip() != '',
             f'{what} must be a non-empty string.')
    parts = [part.strip().strip('[]') for part in name.split('.')]
    for part in parts:
        _require(bool(_IDENTIFIER.match(part)),
                 f'{what} contains an invalid SQL identifier: {part!r}.')
    return '.'.join(f'[{part}]' for part in parts)


class Check:
    """One validation applied to one or more vocabulary keys of an entity type."""

    def __init__(self, dimension: str, definition, entity_type: str):
        if isinstance(definition, str):
            definition = {'key': definition}
        _require(isinstance(definition, dict),
                 f'{entity_type}: each {dimension} check must be a string or an object.')

        keys = definition.get('keys')
        if keys is None:
            key = definition.get('key')
            _require(isinstance(key, str),
                     f'{entity_type}: a {dimension} check needs "key" or "keys".')
            keys = [key]
        _require(isinstance(keys, list) and len(keys) > 0
                 and all(isinstance(k, str) for k in keys),
                 f'{entity_type}: "keys" must be a non-empty list of vocabulary keys.')

        rule = definition.get('rule', DEFAULT_RULES.get(dimension))
        _require(isinstance(rule, str),
                 f'{entity_type}: {dimension} check on {keys[0]} needs a "rule".')

        self.dimension = dimension
        self.keys = keys
        self.rule = rule
        self.options = {k: v for k, v in definition.items()
                        if k not in ('key', 'keys', 'rule', 'name')}
        self.name = definition.get('name') or \
            f"{dimension.replace('_', ' ').title()} of {' and '.join(keys)}"


class EntityTypeConfig:
    """Metric definitions for a single CluedIn entity type."""

    def __init__(self, definition: dict):
        _require(isinstance(definition, dict),
                 'Each item of "entity_types" must be an object.')
        entity_type = definition.get('entity_type')
        _require(isinstance(entity_type, str) and entity_type != '',
                 'Each entity type needs a non-empty "entity_type".')

        metrics = definition.get('metrics', {})
        _require(isinstance(metrics, dict),
                 f'{entity_type}: "metrics" must be an object keyed by dimension.')

        self.entity_type = entity_type
        self.label = definition.get('label', entity_type)
        self.dynamic_metrics = definition.get('dynamic_metrics')
        self.checks = []
        for dimension, definitions in metrics.items():
            _require(isinstance(definitions, list),
                     f'{entity_type}: "{dimension}" must be a list of checks.')
            for check in definitions:
                self.checks.append(Check(dimension, check, entity_type))


class ReferenceSetConfig:
    """A set of values collected from one entity type, used by membership rules."""

    def __init__(self, name: str, definition: dict):
        _require(isinstance(definition, dict),
                 f'Reference set "{name}" must be an object.')
        entity_type = definition.get('entity_type')
        key = definition.get('key')
        _require(isinstance(entity_type, str) and entity_type != '',
                 f'Reference set "{name}" needs an "entity_type".')
        _require(isinstance(key, str) and key != '',
                 f'Reference set "{name}" needs a vocabulary "key".')
        ignore_values = definition.get('ignore_values', [])
        _require(isinstance(ignore_values, list),
                 f'Reference set "{name}": "ignore_values" must be a list.')

        self.name = name
        self.entity_type = entity_type
        self.key = key
        self.ignore_values = set(ignore_values)


class SqlConfig:
    """Target table and column names for the metric history table."""

    def __init__(self, definition: dict):
        _require(isinstance(definition, dict), '"sql" must be an object.')

        table = os.getenv('METRICS_TABLE') or definition.get('table')
        _require(bool(table),
                 'No metrics table configured. Set METRICS_TABLE or "sql.table".')

        columns = dict(DEFAULT_COLUMNS)
        overrides = definition.get('columns', {})
        _require(isinstance(overrides, dict), '"sql.columns" must be an object.')
        unknown = set(overrides) - set(DEFAULT_COLUMNS)
        _require(not unknown,
                 f'Unknown "sql.columns" entries: {", ".join(sorted(unknown))}.')
        columns.update(overrides)

        self.table = validate_identifier(table, 'The metrics table')
        # A column mapped to null is omitted from the INSERT.
        self.columns = {
            role: validate_identifier(name, f'Column "{role}"')
            for role, name in columns.items() if name is not None
        }
        for role in ('name', 'value'):
            _require(role in self.columns,
                     f'Column "{role}" may not be disabled.')


class Config:
    """The complete metrics configuration."""

    def __init__(self, definition: dict):
        _require(isinstance(definition, dict),
                 'The configuration file must contain a JSON object.')

        entity_types = definition.get('entity_types', [])
        _require(isinstance(entity_types, list) and len(entity_types) > 0,
                 '"entity_types" must list at least one entity type.')

        reference_sets = definition.get('reference_sets', {})
        _require(isinstance(reference_sets, dict),
                 '"reference_sets" must be an object.')

        dynamic = definition.get('dynamic_metrics', {})
        _require(isinstance(dynamic, dict), '"dynamic_metrics" must be an object.')

        self.title = definition.get('title', 'Data Quality Metrics')
        self.entity_types = [EntityTypeConfig(e) for e in entity_types]
        self.reference_sets = {
            name: ReferenceSetConfig(name, value)
            for name, value in reference_sets.items()
        }
        self.sql = SqlConfig(definition.get('sql', {}))

        self.dynamic_enabled = dynamic.get('enabled', True)
        self.dynamic_prefix = dynamic.get('vocabulary_key_prefix', 'metric')
        self.dynamic_true_values = set(dynamic.get('true_values', ['true']))
        _require(isinstance(self.dynamic_prefix, str) and self.dynamic_prefix != '',
                 '"dynamic_metrics.vocabulary_key_prefix" must be a non-empty string.')

        self.missing_value = definition.get('missing_value', DEFAULT_MISSING_VALUE)
        self.page_size = definition.get('page_size', 10_000)
        _require(isinstance(self.page_size, int) and self.page_size > 0,
                 '"page_size" must be a positive integer.')

        self._validate_references()

    def _validate_references(self):
        """Fail early when a check names a reference set that does not exist."""
        for entity_type in self.entity_types:
            for check in entity_type.checks:
                name = check.options.get('reference_set')
                if name is None:
                    continue
                _require(name in self.reference_sets,
                         f'{entity_type.entity_type}: check "{check.name}" refers to '
                         f'unknown reference set "{name}".')

    def entity_types_to_load(self) -> list:
        """List every entity type to fetch, including reference-set sources.

        Returns:
            list: entity types, de-duplicated, in first-seen order.
        """
        ordered = []
        for entity_type in self.entity_types:
            if entity_type.entity_type not in ordered:
                ordered.append(entity_type.entity_type)
        for reference_set in self.reference_sets.values():
            if reference_set.entity_type not in ordered:
                ordered.append(reference_set.entity_type)
        return ordered

    def dynamic_metric_entity_types(self) -> list:
        """List entity types that opt in to dynamic metrics.

        Returns:
            list: entity types to scan for prefixed metric properties.
        """
        if not self.dynamic_enabled:
            return []
        return [e.entity_type for e in self.entity_types
                if e.dynamic_metrics is not False]


def load_config(path: str = None) -> Config:
    """Load the configuration file.

    Args:
        path (str, optional): path to the file. Defaults to $METRICS_CONFIG, then
            to config/metrics.json.

    Returns:
        Config: the validated configuration.
    """
    path = path or os.getenv('METRICS_CONFIG') or DEFAULT_CONFIG_PATH
    try:
        with open(path, 'r', encoding='utf-8') as file:
            definition = json.load(file)
    except FileNotFoundError as error:
        raise ConfigError(
            f'Configuration file not found: {path}. '
            'Copy config/metrics.example.json and set METRICS_CONFIG.') from error
    except json.JSONDecodeError as error:
        raise ConfigError(f'{path} is not valid JSON: {error}') from error
    return Config(definition)
