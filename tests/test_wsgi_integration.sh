#!/bin/sh
# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.
set -e

apt-get -y install git sudo make postgresql-all
apt-get -y install apache2

make venv
. venv/bin/activate

make install-deps

sudo -u postgres scripts/database_create.sh sner sner
sudo -u postgres psql -c "ALTER USER sner WITH ENCRYPTED PASSWORD 'password';"
mkdir -p /var/lib/sner
chown www-data /var/lib/sner

cat > /etc/sner.yaml <<_EOF_
server:
    secret: 'testsecret'
    application_root: '/sner'
    db: 'postgresql://sner:password@localhost/sner'
_EOF_
make db

cp extra/apache_proxy.conf /etc/apache2/conf-enabled/sner.conf
a2enmod proxy
a2enmod proxy_http
systemctl restart apache2

cp extra/sner.service /etc/systemd/system/sner.service
systemctl daemon-reload
systemctl enable --now sner

curl http://localhost/sner/
