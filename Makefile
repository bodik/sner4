.PHONY: all venv install-deps freeze db-create-default db-create-test db lint flake8 pylint test coverage install-extra test-extra

all: lint coverage


venv:
	sudo apt-get -y install python-virtualenv python3-virtualenv
	virtualenv -p python3 venv


install-deps:
	# base installation
	sudo apt-get -y install unzip nmap ipv6toolkit
	# required by psycopg2
	sudo apt-get -y install gcc python3-dev libpq-dev
	pip install -r requirements.lock
	# remove after update to selenium 4.x
	if [ -d venv/lib/python3.7/site-packages/selenium ]; then patch --backup --directory=venv/lib/python3.7/site-packages/selenium --strip=3 < extra/fix-python-selenium-resourcewarning.patch; fi
	if [ -d /home/travis/virtualenv/python3.7.6/lib/python3.7/site-packages/selenium ]; then patch --backup --directory=/home/travis/virtualenv/python3.7.6/lib/python3.7/site-packages/selenium --strip=3 < extra/fix-python-selenium-resourcewarning.patch; fi
	if [ -d /opt/hostedtoolcache/Python/3.7.9/x64/lib/python3.7/site-packages/selenium ]; then patch --backup --directory=/opt/hostedtoolcache/Python/3.7.9/x64/lib/python3.7/site-packages/selenium --strip=3 < extra/fix-python-selenium-resourcewarning.patch; fi

freeze:
	@pip freeze | grep -v '^pkg-resources='


db-create-default:
	sudo -u postgres psql -c "CREATE DATABASE sner" | true
	sudo -u postgres psql -c "CREATE USER ${USER}" | true
	mkdir -p /var/lib/sner

db-create-test:
	sudo -u postgres psql -c "CREATE DATABASE sner_test" | true
	sudo -u postgres psql -c "CREATE USER ${USER}" | true
	mkdir -p /tmp/sner_test_var

db:
	bin/server db remove
	bin/server db init
	bin/server db init-data


lint: flake8 pylint
flake8:
	python -m flake8 sner bin/agent bin/server tests
pylint:
	python -m pylint sner bin/agent bin/server tests

test:
	python -m pytest -v tests/server tests/agent

coverage:
	coverage run --source sner -m pytest tests/server tests/agent -x -vv
	coverage report --show-missing --fail-under 100


install-extra: /usr/local/bin/geckodriver
	which firefox || sudo apt-get -y install firefox-esr

/usr/local/bin/geckodriver:
	rm -f /tmp/geckodriver.tar.gz
	wget --no-verbose -O /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz
	sudo tar xzf /tmp/geckodriver.tar.gz -C /usr/local/bin geckodriver

test-extra:
	python -m pytest -x -vv tests/selenium
