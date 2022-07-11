#!/bin/sh
# development helper

if [ -z "$1" ]; then
	echo "ERROR: dump filename required"
	exit 1
fi

pg_dump \
	--clean \
	--exclude-table=user \
	--exclude-table=user_id_seq \
	--exclude-table=webauthn_credential \
	--exclude-table=webauthn_credential_id_seq \
	sner \
	> $1
