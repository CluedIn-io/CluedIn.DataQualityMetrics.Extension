"""Calls to CluedIn's API."""
import os

import cluedin

SEARCH_QUERY = """
    query searchEntities($cursor: PagingCursor, $query: String, $pageSize: Int) {
    search(query: $query, sort: DATE, cursor: $cursor, pageSize: $pageSize) {
        totalResults
        cursor
        entries {
            id
            name
            entityType
            properties
        }
    }
    }
"""


def get_context() -> cluedin.Context:
    """Get CluedIn context.

    Returns:
        cluedin.Context: CluedIn context.
    """

    return cluedin.Context.from_dict({
        'access_token': os.getenv('CLUEDIN_ACCESS_TOKEN'),
        'domain': os.getenv('CLUEDIN_DOMAIN'),
        'org_name': os.getenv('CLUEDIN_ORG_NAME'),
        'verify_tls': os.getenv('CLUEDIN_VERIFY_TLS')
    })


def get_entities_by_type(entity_type: str, page_size: int = 10_000) -> list:
    """Get all entities of one entity type.

    Args:
        entity_type (str): Entity type, for example /Example/Port.
        page_size (int, optional): search page size. Defaults to 10 000.

    Returns:
        list: List of entities.
    """
    variables = {
        'query': f'entityType:{entity_type}',
        'pageSize': page_size
    }

    return list(cluedin.gql.entries(get_context(), SEARCH_QUERY, variables))
