#/usr/bin/python

import sys
import os

def main(argv):

	# Check we have the correct arguments.
	if len(argv) != 2:
		print ("Usage: mytest.py CROPPED_DIR ORIGINAL_DIR")
		sys.exit(2)

	# Setup our directories.
	croppedImageDir = argv[0]
	originalImageDir = argv[1]

	# Get list of images in cropped directory.
	imageList = os.listdir(croppedImageDir)

	# Loop through image names.
	for imageName in imageList:
		processImage(croppedImageDir + imageName, originalImageDir + imageName)

		# Temporary break to limit to first result.
		break

	print ("Done.")

def processImage(croppedImage, originalImage):

	print (croppedImage)
	print (originalImage)

if __name__ == "__main__":
	main(sys.argv[1:])