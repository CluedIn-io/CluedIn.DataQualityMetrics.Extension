"""Evaluate configured data quality metrics for an entity type."""
from collections import defaultdict
from datetime import datetime

from dto import MetricHistoryRecord
from rules import MULTI_VALUE_RULES, get_property, get_rule

UNIQUE_RULE = 'unique'


def build_reference_sets(config, entities_by_type: dict) -> dict:
    """Collect the value sets that membership rules are checked against.

    Args:
        config (Config): the metrics configuration.
        entities_by_type (dict): loaded entities keyed by entity type.

    Returns:
        dict: reference set name -> set of values.
    """
    reference_sets = {}
    for name, definition in config.reference_sets.items():
        values = set()
        for entity in entities_by_type.get(definition.entity_type, []):
            value = get_property(entity, definition.key)
            if value is None or value in definition.ignore_values:
                continue
            values.add(value)
        reference_sets[name] = values
    return reference_sets


def _check_options(check, reference_sets: dict) -> dict:
    """Resolve a check's options, injecting the reference set it names.

    Args:
        check (Check): the configured check.
        reference_sets (dict): reference set name -> set of values.

    Returns:
        dict: options passed to the rule function.
    """
    options = dict(check.options)
    name = options.get('reference_set')
    if name is not None:
        options['_resolved_reference_set'] = reference_sets.get(name, set())
    return options


def _evaluate(check, entity: dict, options: dict) -> bool:
    """Apply one check to one entity.

    Args:
        check (Check): the configured check.
        entity (dict): the entity.
        options (dict): resolved rule options.

    Returns:
        bool: True when the entity passes.
    """
    rule = get_rule(check.rule)
    values = [get_property(entity, key) for key in check.keys]
    if check.rule in MULTI_VALUE_RULES:
        return bool(rule(values, options))
    return all(bool(rule(value, options)) for value in values)


def _unique_value(check, entity: dict, missing_value: str):
    """Build the value whose distinct count a uniqueness check reports.

    Args:
        check (Check): the configured check.
        entity (dict): the entity.
        missing_value (str): stand-in for an absent property in a composite key.

    Returns:
        The property value, or the joined values of a composite key.
    """
    if len(check.keys) == 1:
        return get_property(entity, check.keys[0])
    return ','.join(
        get_property(entity, key, missing_value) for key in check.keys)


def calculate_entity_type_metrics(
        config, entity_type_config, entities: list, reference_sets: dict) -> list:
    """Calculate every configured metric for one entity type.

    Args:
        config (Config): the metrics configuration.
        entity_type_config (EntityTypeConfig): the entity type's metric definitions.
        entities (list): the entities of that type.
        reference_sets (dict): reference set name -> set of values.

    Returns:
        list: MetricHistoryRecord for each metric.
    """
    now = datetime.utcnow()
    total = len(entities)
    if total == 0:
        return []

    counts = defaultdict(lambda: 0)
    sets = defaultdict(set)
    checks = entity_type_config.checks

    resolved = {id(check): _check_options(check, reference_sets) for check in checks}

    for entity in entities:
        for check in checks:
            if check.rule == UNIQUE_RULE:
                sets[check.name].add(
                    _unique_value(check, entity, config.missing_value))
            elif _evaluate(check, entity, resolved[id(check)]):
                counts[check.name] += 1

    records = []

    # Emit a record for every non-uniqueness check, including those nothing passed.
    for check in checks:
        if check.rule == UNIQUE_RULE:
            continue
        passed = counts[check.name]
        records.append(MetricHistoryRecord(
            date=now,
            name=check.name,
            value=passed / total,
            info=f'{passed} passed out of {total}'))

    for check in checks:
        if check.rule != UNIQUE_RULE or len(sets[check.name]) == 0:
            continue
        distinct = len(sets[check.name])
        records.append(MetricHistoryRecord(
            date=now,
            name=check.name,
            value=distinct / total,
            info=f'{distinct} unique out of {total}'))

    return records


def calculate_dynamic_metrics(config, entity_type: str, entities: list) -> list:
    """Calculate metrics that CluedIn itself evaluated into prefixed properties.

    Any property named ``property-<prefix>...`` is treated as a boolean metric, so a
    rule authored as a vocabulary key is reported without a change to this repository.

    Args:
        config (Config): the metrics configuration.
        entity_type (str): the entity type being scanned.
        entities (list): the entities of that type.

    Returns:
        list: MetricHistoryRecord for each discovered metric.
    """
    now = datetime.utcnow()
    total = len(entities)
    if total == 0:
        return []

    prefix = f'property-{config.dynamic_prefix}'
    counts = defaultdict(lambda: 0)

    for entity in entities:
        for property_name, property_value in entity['properties'].items():
            if not property_name.startswith(prefix):
                continue
            name = f'{entity_type} {property_name}'
            # Register the metric even when no entity passes it.
            counts[name] += 1 if property_value in config.dynamic_true_values else 0

    return [
        MetricHistoryRecord(
            date=now,
            name=name,
            value=passed / total,
            info=f'{passed} passed out of {total}')
        for name, passed in counts.items()
    ]
