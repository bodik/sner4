#!/usr/bin/env python3
"""
used to generate batch file from `bin/server storage service-list` command.

## Usage

```
bin/server storage service-list --filter 'Service.name ilike "%http%"' > targets.txt
python3 scripts/nikto_batch_generator.py targets.txt > nikto_commands.txt
parallel --dry-run -j 3 /bin/sh -c "{}" :::: nikto_commands.txt
```
"""

import re
from argparse import ArgumentParser
from pathlib import Path


def main():
    """main"""

    parser = ArgumentParser()
    parser.add_argument('inputfile')
    args = parser.parse_args()

    targets = Path(args.inputfile).read_text().splitlines()
    for target in targets:
        match = re.match('(?P<proto>.*)://(?P<host>.*):(?P<port>.*)', target)
        if match:
            ssl = ' -ssl' if match['port'] == '443' else ''
            output = f'output_{match["host"]}_{match["port"]}.txt'
            print(f'nikto -host {match["host"]} -port {match["port"]}{ssl} -output {output}')


if __name__ == '__main__':
    main()
