#!/bin/bash
# This file is part of sner4 project governed by MIT license, see the LICENSE.txt file.

TOTAL_SEGMENTS=$(( 50*(10**6) / (256**2) ))
FIRST_OCTET=10
SECOND_OCTET=0

ROUND=0
while [[ $ROUND -lt $TOTAL_SEGMENTS ]]; do
	FIRST_OCTET=$(( 10 + (ROUND / 256) ))
	SECOND_OCTET=$(( ROUND % 256 ))
	NET="${FIRST_OCTET}.${SECOND_OCTET}.0.0/16"

	echo "## round $ROUND $NET"
	bin/server scheduler enumips "$NET" | bin/server scheduler queue-enqueue 'dev dummy' --file=-

	ROUND=$((ROUND+1))
done
