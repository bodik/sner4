#!/bin/sh

which firefox || apt-get -y install firefox-esr
wget --no-verbose -O /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.30.0/geckodriver-v0.30.0-linux64.tar.gz
tar xzf /tmp/geckodriver.tar.gz -C /usr/local/bin geckodriver
