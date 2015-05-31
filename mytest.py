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
import PIL.ImageOps

croppedImageDir = ""
originalImageDir = ""
outputDir = ""

def main(argv):

	# Check we have the correct arguments.
	if len(argv) != 3:
		print ("Usage: mytest.py CROPPED_DIR ORIGINAL_DIR OUTPUT_DIR")
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
		break


def processImage(imageName):

	print "Processing:", imageName + "..."

	croppedImage = Image.open(croppedImageDir + imageName)
	originalImage = Image.open(originalImageDir + imageName)

	result, foundImage = existsInside(croppedImage, originalImage)

	if result == 1:
		foundImage.save(outputDir + "new" + imageName)

	return


def existsInside(childImage, parentImage, depth = 0):

	# Time to give up?
	if depth > 4:
		return 0, object()

	# Check is not smaller than child.
	if parentImage.size[0] < childImage.size[0] or parentImage.size[1] < childImage.size[1]:
		print "Parent is smaller than child!"
		return

	# Resize images.
	originalParent = parentImage
	originalChild = childImage

	if parentImage.size[0] > 1000:

		originalParent = parentImage
		originalChild = childImage

		parentImage, multiplier = resizeImage(parentImage, 1000)
		childImage, multiplier = resizeImage(childImage, int(childImage.size[0] * multiplier))

	parentImage.save("smParent.jpg")
	childImage.save("smChild.jpg")

	# Get child sample.
	childImageSize = childImage.size
	parentImageSize = parentImage.size

	sampleSize = (math.trunc(parentImageSize[0] * 0.03), math.trunc(parentImageSize[0] * 0.03))

	childSample, childSampleOrigin = getSample(childImage, sampleSize)
	
	childSample.save("childSample.jpg")

	print "Sample origin:", childSampleOrigin
	print "Sample size:", sampleSize

	# Testing setup
	samplePixelCount = sampleSize[0] * sampleSize[1]

	requiredMatch = 0.2
	bestSamplePositions = []

	bestFullMatch = 0
	bestFullPosition = ()

	# Width loop.
	for x in range(0, parentImageSize[0] - sampleSize[0]):

		percentComplete = int((100 * (x / float(parentImageSize[0]))) / 2) + 1

		sys.stdout.write("\rSamples: {2}\t[{0}{1}]".format("=" * percentComplete, "-" * (50 - percentComplete), len(bestSamplePositions)))
		sys.stdout.flush()

		# Height loop.
		for y in range(0, parentImageSize[1] - sampleSize[1]):

			testPos = (x, y)

			# Sample parent.
			parentSample = sampleImage(parentImage, testPos, sampleSize)
			result = quickCompare(childSample, parentSample)

			# Above requirement?
			if result:

				# Add to samples.
				bestSamplePositions.append(testPos)

	print

	# Loop saved samples.
	for samPos in bestSamplePositions:
		cropOrigin = (samPos[0] - childSampleOrigin[0], samPos[1] - childSampleOrigin[1])

		# Test full child.
		parentCrop = sampleImage(parentImage, cropOrigin, childImageSize)
		result = compareImages(parentCrop, childImage, 20, 0)

		# Better than best?
		if result > bestFullMatch:
			
			# Record new best.
			bestFullMatch = result
			bestFullPosition = cropOrigin

	# print(gc.get_count())
	gc.collect()
	# print(gc.get_count())

	# Got a best match?
	if bestFullMatch > 0:

		print "Best match: ({0}/{1}) {2:.2f}%".format(bestFullMatch, childImageSize[0] * childImageSize[1], (float(bestFullMatch) / (childImageSize[0] * childImageSize[1])) * 100)
		cropOrigin = (math.trunc(bestFullPosition[0] / multiplier), math.trunc(bestFullPosition[1] / multiplier))
		cropSize = originalChild.size

		parentCrop = sampleImage(originalParent, cropOrigin, cropSize)
		return 1, parentCrop

	return existsInside(originalChild, originalParent, depth + 1)

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

	multiplier = toWidth / float(img.size[0])
	aspectRatio = img.size[1] / float(img.size[0])

	newWidth = math.trunc(img.size[0] * multiplier)
	newSize = (newWidth, int(newWidth * aspectRatio))

	newImg = img.resize(newSize, Image.LANCZOS)

	return newImg, multiplier


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

		imgASam = sampleImage(imgA, samplePoint, (1, 1))
		imgBSam = sampleImage(imgB, samplePoint, (1, 1))

		result = compareImages(imgASam, imgBSam, 7)

		if result < 1:
			return 0

	# Good sample!
	return 1

def compareImages(imgA, imgB, variance = 16, output = 0):

	# Check dimensions are equal.
	if imgA.size != imgB.size:
		print "Images not the same dimensions!"
		return

	overlay = imageOverlay(imgA, imgB)

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

	overlay.close()

	return matches

def imageOverlay(imgA, imgB):

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

	return overlay


if __name__ == "__main__":
	os.system("clear")
	startTime = time.time()
	main(sys.argv[1:])
	print "--- %s seconds ---" % (time.time() - startTime)