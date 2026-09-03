"""Download every entity of one entity type from CluedIn to a JSON file.

Useful for inspecting the properties available on an entity type before writing the
checks for it in the metrics configuration.

Credentials come from the same environment variables as metrics.py, so a local .env
file is enough:

    python scripts/download_entities.py /Example/Location -o locations.json

Alternatively, point --context at a CluedIn SDK context file:

    {
      "domain": "example.com",
      "org_name": "example",
      "access_token": "...",
      "verify_tls": false
    }
"""
import argparse
import json
import os
import sys

import cluedin
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import get_context  # noqa: E402  pylint: disable=wrong-import-position

QUERY = """
    query searchEntities($cursor: PagingCursor, $query: String, $pageSize: Int) {
      search(query: $query, sort: FIELDS, cursor: $cursor, pageSize: $pageSize
             sortFields: {field: "id", direction: ASCENDING}
      ) { totalResults cursor entries { id name entityType codes properties } } }
"""


def parse_args(argv=None):
    """Parse command line arguments.

    Args:
        argv (list, optional): arguments to parse. Defaults to sys.argv[1:].

    Returns:
        argparse.Namespace: the parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__.split('\n', maxsplit=1)[0])
    parser.add_argument(
        'entity_type', help='Entity type to download, for example /Example/Location.')
    parser.add_argument(
        '-o', '--output', default='entities.json', help='Output file.')
    parser.add_argument(
        '--context', help='Path to a CluedIn SDK context JSON file. '
                          'Defaults to the CLUEDIN_* environment variables.')
    parser.add_argument(
        '--page-size', type=int, default=10_000, help='Search page size.')
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Download the entities and write them to the output file.

    Args:
        argv (list, optional): command line arguments.

    Returns:
        int: process exit code.
    """
    args = parse_args(argv)
    load_dotenv()

    context = cluedin.Context.from_json_file(args.context) if args.context \
        else get_context()

    variables = {
        'query': f'entityType:{args.entity_type}',
        'pageSize': args.page_size,
    }

    entities = cluedin.gql.entries(context=context, query=QUERY, variables=variables)
    entities = sorted(entities, key=lambda entity: entity['name'])

    with open(args.output, 'w', encoding='utf-8') as file:
        json.dump(entities, file, ensure_ascii=False, indent=2, sort_keys=False)

    print(f'{len(entities)} {args.entity_type} written to {args.output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
