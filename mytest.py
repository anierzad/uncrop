#/usr/bin/python

import sys
import os
import time
import math
import random
import gc

from guppy import hpy
from PIL import Image
from PIL import ImageStat
from PIL import ImageFilter
from PIL import ImageOps
from PIL import ImageChops

croppedImageDir = ""
originalImageDir = ""
outputDir = ""

def main(argv):

	# Check we have the correct arguments.
	if len(argv) != 3:
		print "Usage: mytest.py CROPPED_DIR ORIGINAL_DIR OUTPUT_DIR"
		sys.exit(2)

	# Setup our directories.
	global croppedImageDir
	global originalImageDir
	global outputDir

	croppedImageDir = argv[0]
	originalImageDir = argv[1]
	outputDir = argv[2]

	# Get list of images in cropped directory.
	imageList = os.listdir(croppedImageDir)

	# Loop through image names.
	for imageName in imageList:
		processImage(imageName)

		# Temporary break to limit to first result.
		# break


def processImage(imageName):

	print "Processing:", imageName + "..."

	# Test unscaled.
	croppedImage = Image.open(croppedImageDir + imageName)
	originalImage = Image.open(originalImageDir + imageName)

	result, matchPer, origin = existsInside(croppedImage, originalImage)

	if result == 1:
		print "NO SCALE PASS REQUIRED!"
		return True

	# Start scaled tests.
	bestPercentage = 0.0
	bestOrigin = (0, 0)
	bestScale = 0.0
	bestWidth = 0

	inRunOver = False
	runOverPos = 0
	runOverMax = 10

	# Get close.
	startPoint = 0

	for width in range(croppedImage.size[0], originalImage.size[0]):

		# Test the first ten fully.
		if width < croppedImage.size[0] + 10:

			result, matchPer, origin, magnitude = testWidth(width, croppedImage, originalImage)

			# Any matches?
			if result:

				# Set the start point at the start.
				startPoint = croppedImage.size[0]
				break
		else:

			# Test every ten.
			if width % 10 == 0:
				result, matchPer, origin, magnitude = testWidth(width, croppedImage, originalImage)

				# Any matches?
				if result:

					# Set the start point to ten back.
					startPoint = width - 10
					break


	for width in range(startPoint, originalImage.size[0]):

		result, matchPer, origin, magnitude = testWidth(width, croppedImage, originalImage)

		if result:
			print "Width {0} matched {1}.".format(width, matchPer)

			# Enter run over.
			inRunOver = True

			# Better match than current best percentage?
			if matchPer > bestPercentage:

				# Set as best.
				bestPercentage = matchPer
				bestOrigin = origin
				bestScale = magnitude
				bestWidth = width

				# Reset run over.
				runOverPos = 0

		if inRunOver:
			runOverPos = runOverPos + 1
			if runOverPos >= runOverMax:
				break

	# Results.
	print "Would use width {0} which matched {1:.2f}%.".format(bestWidth, bestPercentage)

	newCropSize = enlargeDimensions(croppedImage.size, bestScale)
	newCropOrigin = (int((originalImage.size[0] * bestOrigin[0]) + 0.5), int((originalImage.size[1] * bestOrigin[1]) + 0.5))

	print "NewCrop: {0} at {1}".format(newCropSize, newCropOrigin)

	newCropImg = sampleImage(originalImage, newCropOrigin, newCropSize)

	newCropImg.save(outputDir + "/" + imageName, "jpeg", quality=100)


def testWidth(width, cImg, oImg):

	result = object # Match found at this width?

	# Resize original image.
	resized, scale = resizeImage(oImg, width)

	# Test to see if the cropped image exists inside the resized image.
	result, matchPer, origin = existsInside(cImg, resized)

	return result, matchPer, origin, scale


def existsInside(childImage, parentImage):

	# Check is not smaller than child.
	if parentImage.size[0] < childImage.size[0] or parentImage.size[1] < childImage.size[1]:
		print "Parent is smaller than child!"
		return

	# Resize images.
	targetSize = 600
	multiplier = 1.0
	originalParent = parentImage
	originalChild = childImage

	if parentImage.size[0] > targetSize:

		originalParent = parentImage
		originalChild = childImage

		parentImage, multiplier = resizeImage(parentImage, targetSize)
		childImage, multiplier = resizeImage(childImage, int(childImage.size[0] * multiplier))

	parentImage.save("smParent.jpg")
	childImage.save("smChild.jpg")

	# Get child sample.
	childImageSize = childImage.size
	parentImageSize = parentImage.size

	sampleSize = (math.trunc(parentImageSize[0] * 0.05), math.trunc(parentImageSize[0] * 0.05))

	childSample = childImage
	childSampleOrigin = (0,0)#getSample(childImage, sampleSize)

	sampleSize = childSample.size
	
	childSample.save("childSample.jpg")

	# Testing setup
	samplePixelCount = sampleSize[0] * sampleSize[1]

	requiredMatch = 0.2
	bestSamplePositions = []

	bestFullMatch = 0
	bestFullPosition = ()

	# Width loop.
	for x in range(0, parentImageSize[0] - sampleSize[0]):

		percentComplete = int((100 * (x / float(parentImageSize[0] - sampleSize[0]))) / 2) + 1

		sys.stdout.write("\r[{0}{1}] ParRes: {3}, Samples Matched: {2}".format("=" * percentComplete, "-" * (50 - percentComplete), len(bestSamplePositions), originalParent.size))
		sys.stdout.flush()

		# Height loop.
		for y in range(0, parentImageSize[1] - sampleSize[1]):

			testPos = (x, y)

			# Sample parent.
			parentSample = sampleImage(parentImage, testPos, sampleSize)
			result = quickCompare(childSample, parentSample)

			# Above requirement?
			if result == 1:

				# Add to samples.
				bestSamplePositions.append(testPos)

	print

	# Loop saved samples.
	for samPos in bestSamplePositions:
		cropOrigin = (samPos[0] - childSampleOrigin[0], samPos[1] - childSampleOrigin[1])

		# Test full child.
		parentCrop = sampleImage(parentImage, cropOrigin, childImageSize)
		result, matches = compareImages(parentCrop, childImage)

		# Better than best?
		if matches > bestFullMatch:
			
			# Record new best.
			bestFullMatch = matches
			bestFullPosition = cropOrigin

	# print(gc.get_count())
	gc.collect()
	# print(gc.get_count())

	# Got a best match?
	if bestFullMatch > 0:

		# print "Trying to beat {0} at {1}".format(bestFullMatch, bestFullPosition)

		# Final wiggle!
		for x in range(bestFullPosition[0] - 5, bestFullPosition[0] + 5):
			for y in range(bestFullPosition[1] - 5, bestFullPosition[1] + 5):
				cropOrigin = (x - childSampleOrigin[0], y - childSampleOrigin[1])

				# Test full child.
				parentCrop = sampleImage(parentImage, cropOrigin, childImageSize)
				result, matches = compareImages(parentCrop, childImage)

				# Better than best?
				if matches > bestFullMatch:

					# Record new best.
					bestFullMatch = matches
					bestFullPosition = cropOrigin

		# print "Best match: ({0}/{1}) {2:.2f}%".format(bestFullMatch, childImageSize[0] * childImageSize[1], (float(bestFullMatch) / (childImageSize[0] * childImageSize[1])) * 100)
		bestFullMatchPer = (float(bestFullMatch) / (childImageSize[0] * childImageSize[1])) * 100
		cropOrigin = (math.trunc(bestFullPosition[0] / multiplier), math.trunc(bestFullPosition[1] / multiplier))
		cropSize = originalChild.size

		return True, bestFullMatchPer, (float(bestFullPosition[0]) / float(parentImageSize[0]), float(bestFullPosition[1]) / float(parentImageSize[1]))

	return False, object, object

def getSample(img, size):

	sample = object()
	origin = (0, 0)
	attempts = 0
	variance = 10000

	while 1:
		sample = sampleImage(img, origin, size)

		if testSample(sample, variance):
			break

		origin = (random.randint(0, img.size[0] - size[0]), random.randint(0, img.size[1] - size[1]))

		if attempts >= 10:
			variance = variance - 100
			attempts = 0

		attempts = attempts + 1

	return sample, origin


def testSample(sample, variance):

	var =  ImageStat.Stat(sample).var

	if var[0] + var[1] + var[2] > variance:
		return 1

	return 0


def sampleImage(img, origin = (0, 0), size = (10, 10)):

	x = origin[0]
	y = origin[1]
	w = size[0]
	h = size[1]

	# Check image is larger than sample.
	if img.size[0] < w:
		w = img.size[0]
	if img.size[1] < h:
		h = img.size[1]

	box = (x, y, x + w, y + h)

	# Take sample.
	imgSample = img.crop(box)

	return imgSample

def resizeImage(img, toWidth):

	scale = toWidth / float(img.size[0])

	newSize = calculateDimensions(img.size, scale)

	newImg = img.resize(newSize, Image.LANCZOS)

	return newImg, scale

def calculateDimensions(dimensions, scale):

	aspectRatio = float(dimensions[1]) / float(dimensions[0])

	newWidth = int(round(dimensions[0] * scale))

	newHeight = int(round(newWidth * aspectRatio))

	return (newWidth, newHeight)

def enlargeDimensions(dimensions, scale):

	aspectRatio = float(dimensions[1]) / float(dimensions[0])

	newWidth = int(round(dimensions[0] / scale))

	newHeight = int(round(newWidth * aspectRatio))

	return (newWidth, newHeight)


def quickCompare(imgA, imgB, variance = 16, divide = (3, 3)):

	# Check dimensions are equal.
	if imgA.size != imgB.size:
		print "Images not the same dimensions!"
		return

	# Setup sectors.
	samplePoints = []
	imgSize = imgA.size
	secSize = (int(float(imgSize[0]) / divide[0]), int(float(imgSize[1]) / divide[1]))

	for xSec in range(0, divide[0]):
		for ySec in range(0, divide[1]):

			x = (secSize[0] * xSec) + int(secSize[0] / 2.0)
			y = (secSize[1] * ySec) + int(secSize[1] / 2.0)

			samplePoint = (x, y)
			samplePoints.append(samplePoint)

	# Sample.
	for samplePoint in samplePoints:

		imgASam = sampleImage(imgA, samplePoint, (10, 10))
		imgBSam = sampleImage(imgB, samplePoint, (10, 10))

		result, matches = compareImages(imgASam, imgBSam)

		if result < 1:
			return 0

	# Good sample!
	return 1


def compareImages(imgA, imgB, output = 0, tolerance = 0.4):

	# Check dimensions are equal.
	if imgA.size != imgB.size:
		print "Images not the same dimensions!"
		return

	imgDiff = ImageChops.difference(imgA, imgB)

	# Setup.
	width = imgDiff.size[0]
	height = imgDiff.size[1]
	pixelCount = width * height
	matches = 0
	variance = 26

	# Load overlay in to an array of pixels.
	pixels = imgDiff.load()

	# Width loop.
	for x in range(0, width):

		# Height loop.
		for y in range(0, height):
			
			pixel = pixels[x,y]

			if pixel[0] <= variance and pixel[1] <= variance and pixel[2] <= variance:
				matches = matches + 1


	differences = pixelCount - matches

	avgPixDiff = float(differences) / pixelCount

	if output:
		imgDiff.save(str(matches) + ".jpg")
		# print "Average pixel difference:", avgPixDiff

	if avgPixDiff < tolerance:
		return 1, matches

	return 0, matches


if __name__ == "__main__":
	os.system("clear")
	startTime = time.time()
	main(sys.argv[1:])
	print "--- %s seconds ---" % (time.time() - startTime)