#!/usr/bin/env python3

import base64

# 4 different accounts exist
Accounts = [ 'Installer','Service Partner','Inverter Partner','Admin' ]

AccountBlock = 'B' # This is the currently used block

ignoreLines = True
for line in open('Config.ini', 'r').readlines():
	line = line.strip()

	# skip everything till the correct block
	if line == '[%s]' % AccountBlock:
		ignoreLines = False
		continue
	if ignoreLines:
		continue
	# stop parsing at the end of the correct block
	if len(line) == 0:
		break

	ID,B64 = line.split('=',1)
	ID = int(ID)
	B64str = B64.strip('"')
	if (len(B64str) % 2) == 0:
		B64 = base64.b64decode(B64str)
		s = ''
		for ch in B64:
			s += chr(ch-66)
		print('%18s : %s' % (Accounts[ID-1],s))
	else: # the very last password seems to not be encoded, feels like a bug
		print('%18s : %s ???' % (Accounts[ID-1],B64str))
