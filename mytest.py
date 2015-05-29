#¡/usr/bin/python

import sys
import getopt

def main(argv):
	croppedImageDir = ""
	originalImageDir = ""

	try:
		opts, args = getopt.getopt(argv)
	except getopt.GetoptError:
		print 'mytest.py --croppeddir <croppedfolder> --originaldir <originalfolder>'

