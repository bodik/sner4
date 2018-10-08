#!/bin/sh

rm -f db.sqlite3
export FLASK_APP="sner_web"
flask initdb
