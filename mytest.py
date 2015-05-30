#/usr/bin/python

import sys
import os
import time
import math
import random

from guppy import hpy

from PIL import Image
from PIL import ImageStat
import PIL.ImageOps

logFile = object()

croppedImageDir = ""
originalImageDir = ""
outputDir = ""

def main(argv):

	# Check we have the correct arguments.
	if len(argv) != 3:
		print ("Usage: mytest.py CROPPED_DIR ORIGINAL_DIR OUTPUT_DIR")
		sys.exit(2)

	# Setup logging.
	global logFile
	logFile = open("logFile.txt", "w")
	logFile.truncate()
	logFile.close()

	# Setup our directories.
	global croppedImageDir
	global originalImageDir
	global outputDir

	croppedImageDir = argv[0]
	originalImageDir = argv[1]
	outputDir = argv[2]

	# Get list of images in cropped directory.
	imageList = os.listdir(croppedImageDir)
	print imageList
	# processImage(imageList[1])

	# Loop through image names.
	for imageName in imageList:
		processImage(imageName)

		# Temporary break to limit to first result.
		# break


def processImage(imageName):

	print "Processing:", imageName + "..."

	croppedImage = Image.open(croppedImageDir + imageName)
	originalImage = Image.open(originalImageDir + imageName)

	result, foundImage = existsInside(croppedImage, originalImage)

	if result == 1:
		foundImage.save(outputDir + "new" + imageName);

	return


def existsInside(childImage, parentImage, depth = 0):

	# Time to give up?
	if depth > 4:
		return 0, object()

	# Check is not smaller than child.
	if parentImage.size[0] < childImage.size[0] or parentImage.size[1] < childImage.size[1]:
		print "Parent is smaller than child!"
		return

	# Aim for 1000 pixels
	multiplier = 1000.0 / float(parentImage.size[0])

	if multiplier < 1.0:
		aspectRatio = float(parentImage.size[1]) / float(parentImage.size[0])

		parentNeWidth = math.trunc(parentImage.size[0] * multiplier)
		parentNewSize = (parentNeWidth, int(parentNeWidth * aspectRatio))
		print parentNewSize
		parentImage = parentImage.resize(parentNewSize, Image.LANCZOS)

		childNewWidth = math.trunc(childImage.size[0] * multiplier)
		childNewSize = (childNewWidth, int(childNewWidth * aspectRatio))
		print childNewSize
		childImage = childImage.resize(childNewSize, Image.LANCZOS)

		parentImage.save("smParent.jpg")
		childImage.save("smChild.jpg")

	# Setup.
	chiWidth = childImage.size[0]
	chiHeight = childImage.size[1]
	parWidth = parentImage.size[0]
	parHeight = parentImage.size[1]

	# Get sample size.
	sampleSize = math.trunc(parWidth * 0.01)
	print "Sample size:", sampleSize

	# Sample child.
	xPosChildSample = 0
	yPosChildSample = 0
	attempts = 0
	variance = 10000

	while 1:
		childSample = sampleImage(childImage, xPosChildSample, yPosChildSample, sampleSize, sampleSize)

		if testSample(childSample, variance):
			break

		xPosChildSample = random.randint(0, chiWidth - sampleSize)
		yPosChildSample = random.randint(0, chiHeight - sampleSize)

		if attempts >= 10:
			variance = variance - 100
			attempts = 0

		attempts = attempts + 1
	
	childSample.save("childSample.jpg")

	print "Sample origin:", xPosChildSample, "x", yPosChildSample

	# Testing setup
	samplePixelCount = childSample.size[0] * childSample.size[1]

	requiredMatch = 0.5
	bestSamplePositions = []

	bestFullMatch = 0
	bestFullPosition = ()

	# Width loop.
	for x in range(0, parWidth):

		if x % 100 == 0:
			# print "Progress:", str(x) + "/" + str(parWidth)
			h = hpy()
			print h.heap()

		# Height loop.
		for y in range(0, parHeight):

			# Sample parent.
			parentSample = sampleImage(parentImage, x, y, sampleSize, sampleSize)
			result = compareImages(childSample, parentSample)
			parentSample.close()

			# Above requirement?
			if result / samplePixelCount > requiredMatch:

				bestSamplePositions.append((x, y))
				log("Samples above req.: " + str(len(bestSamplePositions)))

	# Loop saved samples.
	for samPos in bestSamplePositions:
		cropOrigin = (samPos[0] - xPosChildSample, samPos[1] - yPosChildSample)

		# Test full child.
		parentCrop = sampleImage(parentImage, cropOrigin[0], cropOrigin[1], chiWidth, chiHeight)
		result = compareImages(parentCrop, childImage, 20, 1)

		if result > bestFullMatch:
			
			# Record new best.
			bestFullMatch = result
			bestFullPosition = cropOrigin

			# Log.
			log("New best: " + str(bestFullMatch))

	if bestFullMatch > 0:
		parentCrop = sampleImage(parentImage, bestFullPosition[0], bestFullPosition[1], chiWidth, chiHeight)
		return 1, parentCrop

	return existsInside(childImage, parentImage, depth + 1)

def testSample(sample, variance):

	var =  ImageStat.Stat(sample).var

	if var[0] + var[1] + var[2] > variance:
		return 1

	return 0


def sampleImage(img, x = 0, y = 0, w = 7, h = 7):

	# Check image is larger than sample.
	if img.size[0] < w:
		w = img.size[0]
	if img.size[1] < h:
		h = img.size[1]

	box = (x, y, x + w, y + h)

	# Take sample.
	imgSample = img.crop(box)
	imgSample.load()

	return imgSample


def compareImages(imgA, imgB, variance = 16, output = 0):

	# Check dimensions are equal.
	if imgA.size != imgB.size:
		print "Images not the same dimensions!"
		print "imgA:", imgA.size
		print "imgB:", imgB.size
		return

	# Invert.
	imgB = PIL.ImageOps.invert(imgB)

	# Convert to RGBA.
	imgA = imgA.convert("RGBA")
	imgB = imgB.convert("RGBA")

	# Add alpha.
	fiftyGrey = Image.new("L", imgB.size, 128)
	imgB.putalpha(fiftyGrey)
	fiftyGrey.close()

	# Overlay.
	overlay = Image.alpha_composite(imgA, imgB)

	# Setup.
	width = overlay.size[0]
	height = overlay.size[1]
	matches = 0

	# Tolerances
	upperTol = 128 + variance
	lowerTol = 128 - variance

	# Load overlay in to an array of pixels.
	pixels = overlay.load()

	# Width loop.
	for x in range(0, width):

		# Height loop.
		for y in range(0, height):
			
			pixel = pixels[x,y]

			if lowerTol < pixel[0] < upperTol and lowerTol < pixel[1] < upperTol and lowerTol < pixel[2] < upperTol:
				matches = matches + 1

	if output:
		overlay.save(str(matches) + ".jpg")

	# totalPixels = overlay.size[0] * overlay.size[1]

	# if matches / totalPixels > 0.5:
	# 	log("Matched: " + str(matches) + "/" + str(totalPixels))

	overlay.close()

	return matches


def log(line):
	logFile = open("logFile.txt", "w")
	logFile.write(line)
	logFile.write("\n")
	logFile.close()


if __name__ == "__main__":
	startTime = time.time()
	main(sys.argv[1:])
	print "--- %s seconds ---" % (time.time() - startTime)