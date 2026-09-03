"""SQL Server connection and metric history writes."""
import os

import pymssql


def get_connection():
    """Get a connection to the metrics SQL Server.

    Connection settings come from the environment so that no credential is stored in
    the repository or in the configuration file.

    Returns:
        connection: Microsoft SQL Server connection.
    """
    server = os.getenv('METRICS_SQL_SERVER')
    if not server:
        raise RuntimeError(
            'METRICS_SQL_SERVER is not set. See the Parameters section of README.md.')

    settings = {
        'server': server,
        'user': os.getenv('METRICS_SQL_USER'),
        'password': os.getenv('METRICS_SQL_PASSWORD'),
        'database': os.getenv('METRICS_SQL_DATABASE'),
        # Not all conn_properties are compatible with Synapse:
        #   https://github.com/pymssql/pymssql/pull/233/files
        'conn_properties': os.getenv('METRICS_SQL_CONN_PROPERTIES', ''),
    }

    port = os.getenv('METRICS_SQL_PORT')
    if port:
        settings['port'] = port

    return pymssql.connect(**settings)  # pylint: disable=c-extension-no-member


def build_insert(sql_config) -> str:
    """Build the INSERT statement for the configured table and columns.

    Identifiers are validated and bracket-quoted when the configuration is loaded;
    every value is passed as a parameter.

    Args:
        sql_config (SqlConfig): validated table and column names.

    Returns:
        str: the INSERT statement.
    """
    columns = sql_config.columns
    # role -> the expression producing its value.
    expressions = {
        'id': 'NEWID()',
        'name': '%(name)s',
        'value': '%(value)s',
        'info': '%(info)s',
        'created_date': '%(date)s',
        'created_by': '%(user)s',
        'modified_date': '%(date)s',
        'modified_by': 'NULL',
    }

    used = [role for role in expressions if role in columns]
    column_list = ',\n                '.join(columns[role] for role in used)
    # The separator has to precede the comment, or it would be commented out.
    value_list = '\n                '.join(
        f'{expressions[role] + ("," if role != used[-1] else ""):<12}'
        f'-- {columns[role]}'
        for role in used)

    return f"""
            INSERT INTO {sql_config.table}
            (
                {column_list}
            )
            SELECT
                {value_list}
        """


def save_metric_history_record(connection, sql_config, metric_history_record):
    """Save a metric history record.

    Args:
        connection: an open SQL Server connection.
        sql_config (SqlConfig): validated table and column names.
        metric_history_record (MetricHistoryRecord): the record to save.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            build_insert(sql_config),
            {
                'date': metric_history_record.date,
                'info': metric_history_record.info,
                'name': metric_history_record.name,
                'user': os.getenv('METRICS_SQL_USER'),
                'value': metric_history_record.value,
            })
        connection.commit()
