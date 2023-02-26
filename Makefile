.PHONY: all freeze githook install install-db db lint test coverage install-extra test-extra

all: lint coverage

freeze:
	@pip freeze | grep -v '^pkg-resources='

githook:
	ln -sf ../../extra/git_hookprecommit.sh .git/hooks/pre-commit

install:
	sh bin/install.sh
	sh bin/install_nmap.sh
	sh bin/install_ipv6toolkit.sh
	sh bin/install_jarm.sh
	sh bin/install_firefox.sh
	sh bin/install_testssl.sh

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

coverage:
	coverage run --source sner -m pytest tests/agent tests/plugin tests/server -x -vv
	coverage report --show-missing --fail-under 100

install-extra:
	sh bin/install_selenium.sh

test-extra:
	pytest -x -vv tests/selenium
