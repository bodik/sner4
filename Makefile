.PHONY: all install install-extra install-db db lint test test-extra coverage freeze

all: lint coverage

freeze:
	@pip freeze | grep -v '^pkg-resources='

install:
	sh bin/install.sh
	sh bin/install_nmap.sh
	sh bin/install_ipv6toolkit.sh
	sh bin/install_jarm.sh

install-extra:
	sh bin/install_selenium.sh

install-db:
	sh bin/install_db.sh

db:
	bin/server dbx remove
	bin/server dbx init
	bin/server dbx init-data

lint:
	flake8 bin/agent bin/server sner tests
	pylint bin/agent bin/server sner tests

test:
	pytest -v tests/agent tests/plugin tests/server

test-extra:
	pytest -x -vv tests/selenium

coverage:
	coverage run --source sner -m pytest tests/agent tests/plugin tests/server -x -vv
	coverage report --show-missing --fail-under 100
