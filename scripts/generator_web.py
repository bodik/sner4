#!/usr/bin/env python3
"""
used to generate batch file from `bin/server storage service-list` command.

## Usage

```
bin/server storage service-list --filter 'Service.name ilike "%http%" OR Service.name ilike "%www%" --hostnames' > targets.txt
python3 scripts/generator_web.py targets.txt
parallel --dry-run -j 3 /bin/sh -c "{}" :::: targets.txt
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
            proto = 'https' if '443' in match['port'] else 'http'
            print(f'{proto}://{match["host"]}:{match["port"]}')


if __name__ == '__main__':
    main()
