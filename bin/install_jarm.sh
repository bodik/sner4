#!/bin/sh
# install required jarm scanner

git clone --branch sner4-integration https://github.com/bodik/jarm /opt/jarm
ln -sf /opt/jarm/jarm.py /usr/local/bin/jarm
