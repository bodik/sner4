#!/bin/sh

wget --no-verbose -O /tmp/nuclei.zip https://github.com/projectdiscovery/nuclei/releases/download/v2.9.8/nuclei_2.9.8_linux_amd64.zip
unzip /tmp/nuclei.zip -d /opt/nuclei
ln -sf /opt/nuclei/nuclei /usr/local/bin/nuclei