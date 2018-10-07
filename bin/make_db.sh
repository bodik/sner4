#!/bin/sh

rm -f db.sqlite3
export FLASK_APP="sner4web"
flask initdb
