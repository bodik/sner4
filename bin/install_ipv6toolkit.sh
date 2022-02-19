#!/bin/sh
# installs required version of ipv6toolkit

apt-get -y install libpcap-dev
git clone https://github.com/fgont/ipv6toolkit /opt/ipv6toolkit
cd /opt/ipv6toolkit
git checkout babee5e172f680ff18354d9d9918c3f7356d48d3
make all
make install
