"""Calculate data quality metrics for CluedIn entities.

Everything this script measures is declared in a configuration file; see README.md.
"""

import argparse
import sys
import time
import warnings

from dotenv import load_dotenv

from config import ConfigError, load_config
from entity_metrics import (build_reference_sets, calculate_dynamic_metrics,
                            calculate_entity_type_metrics)
from utils import configure_output, print_intro, time_from_start

# api and sql are imported where they are used, so that --validate needs neither the
# CluedIn SDK nor the SQL Server driver.

warnings.filterwarnings('ignore')

load_dotenv()


def parse_args(argv=None):
    """Parse command line arguments.

    Args:
        argv (list, optional): arguments to parse. Defaults to sys.argv[1:].

    Returns:
        argparse.Namespace: the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description='Calculate data quality metrics for CluedIn entities.')
    parser.add_argument(
        '-c', '--config',
        help='Path to the metrics configuration file. '
             'Defaults to $METRICS_CONFIG, then config/metrics.json.')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Calculate and print the metrics without writing to SQL Server.')
    parser.add_argument(
        '--validate', action='store_true',
        help='Validate the configuration file and exit. Contacts nothing.')
    return parser.parse_args(argv)


def load_entities(config, start: float) -> dict:
    """Load every entity type the configuration refers to.

    Args:
        config (Config): the metrics configuration.
        start (float): start time of the script.

    Returns:
        dict: entity type -> list of entities.
    """
    from api import get_entities_by_type  # pylint: disable=import-outside-toplevel

    entities_by_type = {}
    for entity_type in config.entity_types_to_load():
        print(f'{time_from_start(start)} - Loading {entity_type} from CluedIn...')
        entities = get_entities_by_type(entity_type, page_size=config.page_size)
        entities_by_type[entity_type] = entities
        print(f'{time_from_start(start)} - {len(entities)} '
              f'{entity_type} loaded from CluedIn. ✅\n')
    return entities_by_type


def save_records(records: list, config, start: float, dry_run: bool):
    """Write metric history records, or print them on a dry run.

    Args:
        records (list): MetricHistoryRecord to save.
        config (Config): the metrics configuration.
        start (float): start time of the script.
        dry_run (bool): print instead of writing when True.
    """
    if not records:
        print(f'{time_from_start(start)} - No metrics to save.\n')
        return

    if dry_run:
        for record in records:
            print(f'{time_from_start(start)} would save metric history record:'
                  f'\n{record}')
        return

    # pylint: disable-next=import-outside-toplevel
    from sql import get_connection, save_metric_history_record

    with get_connection() as connection:
        for record in records:
            save_metric_history_record(connection, config.sql, record)
            print(f'{time_from_start(start)} saved metric history record:\n{record}')


def calculate_metrics(config_path: str = None, dry_run: bool = False):
    """Calculate data quality metrics for the configured CluedIn entity types.

    Args:
        config_path (str, optional): path to the configuration file.
        dry_run (bool): calculate and print without writing to SQL Server.
    """
    start = time.time()
    config = load_config(config_path)

    print_intro(config.title)

    entities_by_type = load_entities(config, start)
    reference_sets = build_reference_sets(config, entities_by_type)

    for entity_type_config in config.entity_types:
        entity_type = entity_type_config.entity_type
        print(f'{time_from_start(start)} - Calculating data quality metrics '
              f'for {entity_type_config.label}...')
        records = calculate_entity_type_metrics(
            config=config,
            entity_type_config=entity_type_config,
            entities=entities_by_type[entity_type],
            reference_sets=reference_sets)
        save_records(records, config, start, dry_run)
        print(f'{time_from_start(start)} - '
              f'{entity_type_config.label} metrics done ⚓\n\n')

    for entity_type in config.dynamic_metric_entity_types():
        print(f'{time_from_start(start)} - Calculating dynamic data quality metrics '
              f'for {entity_type}...')
        records = calculate_dynamic_metrics(
            config=config,
            entity_type=entity_type,
            entities=entities_by_type[entity_type])
        save_records(records, config, start, dry_run)
        print(f'{time_from_start(start)} - '
              f'{entity_type} dynamic metrics done ⚓\n\n')


def main(argv=None) -> int:
    """Run the script.

    Args:
        argv (list, optional): command line arguments.

    Returns:
        int: process exit code.
    """
    args = parse_args(argv)
    configure_output()
    try:
        if args.validate:
            config = load_config(args.config)
            checks = sum(len(e.checks) for e in config.entity_types)
            print(f'Configuration is valid: {len(config.entity_types)} entity '
                  f'type(s), {checks} check(s), '
                  f'{len(config.reference_sets)} reference set(s).')
            return 0
        calculate_metrics(config_path=args.config, dry_run=args.dry_run)
    except ConfigError as error:
        print(f'Configuration error: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
