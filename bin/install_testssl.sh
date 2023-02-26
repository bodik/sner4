#!/bin/sh

git clone --depth 1 --branch v3.0.8 https://github.com/drwetter/testssl.sh.git /opt/testssl.sh
ln -sf /opt/testssl.sh/testssl.sh /usr/local/bin/testssl.sh
