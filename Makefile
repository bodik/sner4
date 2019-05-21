.PHONY: db db-create-default db-create-test install-deps pylint test test-agent test-server


install-deps:
	apt-get -y install postgresql-all unzip nmap


venv:
	apt-get -y install python-virtualenv python3-virtualenv
	virtualenv -p python3 venv
	venv/bin/pip install -r requirements.txt


db: db-create-default
	#su -c 'bin/database-disconnect.sh sner' postgres
	bin/server db remove
	bin/server db init
	bin/server db initdata


db-create-default:
	su -c "bin/database_create.sh sner ${USER}" postgres
	mkdir -p /var/sner


db-create-test:
	su -c "bin/database_create.sh sner_test ${USER}" postgres
	mkdir -p /tmp/sner_test_var


pylint:
	python -m pylint sner bin/agent bin/server tests


test: test-server test-agent

test-agent: test-server
	sh tests/agent/run_all.sh

test-server: db-create-test
	python -m pytest
