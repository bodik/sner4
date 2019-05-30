.PHONY: all venv install-deps freeze db-create-default db-create-test db lint flake8 pylint test coverage

all: lint coverage


venv:
	# development target
	sudo apt-get -y install python-virtualenv python3-virtualenv
	virtualenv -p python3 venv


install-deps:
	which psql || sudo apt-get -y install postgres-all
	sudo apt-get -y install unzip nmap
	pip install -r requirements.txt

freeze:
	pip freeze | grep -v '^pkg-resources=' > requirements.txt


db-create-default:
	sudo -u postgres bin/database_create.sh sner ${USER}
	mkdir -p /var/sner

db-create-test:
	sudo -u postgres bin/database_create.sh sner_test ${USER}
	mkdir -p /tmp/sner_test_var

db: db-create-default
	#su -c 'bin/database-disconnect.sh sner' postgres
	bin/server db remove
	bin/server db init
	bin/server db initdata


lint: flake8 pylint
flake8:
	python -m flake8 sner bin/agent bin/server tests
pylint:
	python -m pylint sner bin/agent bin/server tests

test: db-create-test
	python -m pytest -v tests/server tests/agent

coverage: db-create-test
	coverage run --source sner -m pytest tests -x -vv
	coverage report --show-missing --fail-under 100
