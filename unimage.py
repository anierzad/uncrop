import random
import math
import gc

from PIL import Image
from PIL import ImageStat
from PIL import ImageChops

class UnImage:

    # Given a pair of dimensions (x, y) and a scale will calculate and return
    # a scaled set of dimensions.
    @staticmethod
    def ScaleDimensions(dimensions, scale):

        aspectRatio = float(dimensions[1]) / float(dimensions[0])

        newWidth = int(round(dimensions[0] * scale))

        newHeight = int(round(newWidth * aspectRatio))

        return (newWidth, newHeight)

    # Get a sample of the working image with sufficient variance to work with.
    @staticmethod
    def GetSample(img, size, origin = (0, 0)):

        # Setup.
        sample = object()
        attempts = 0
        variance = 10000

        while 1:

            # Get sample.
            sample = UnImage.SampleImage(img, size, origin)

            # Test it.
            if UnImage.TestSample(sample, variance):
                break

            origin = (random.randint(0, img.size[0]),
                random.randint(0, img.size[1] - size[1]))

            # Increment attempts.
            attempts = attempts + 1

            # If we've tried 10 times, reduce variance and try again.
            if attempts >=10:
                variance = variance -100
                attempts = 0

        return sample, origin

    # Actually perform the image sample.
    @staticmethod
    def SampleImage(img, size = (10, 10), origin = (0, 0)):

        # Setup.
        x = origin[0]
        y = origin[1]
        w = size[0]
        h = size[1]

        # If image isn't as big as sample size, use image size.
        if img.size[0] < w:
            w = img.size[0]
        if img.size[1] < h:
            h = img.size[1]

        # Build crop box.
        box = (x, y, x + w, y + h)

        # Take sample.
        imgSample = img.crop(box)

        return imgSample

    # Given a sample image and variance, will return whether or not that image
    # meets the passed variance requirement.
    @staticmethod
    def TestSample(sample, variance):

        var =  ImageStat.Stat(sample).var

        if var[0] + var[1] + var[2] > variance:
            return 1

        return 0

    @staticmethod
    def QuickCompare(imgA, imgB, variance = 16, divide = (3, 3)):

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

            imgASam = UnImage.SampleImage(imgA, (10, 10), samplePoint)
            imgBSam = UnImage.SampleImage(imgB, (10, 10), samplePoint)

            result, matches = UnImage.CompareImages(imgASam, imgBSam)

            if result < 1:
                return 0

        # Good sample!
        return 1

    @staticmethod
    def CompareImages(imgA, imgB, output = 0, tolerance = 0.4):

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

    # Constructor.
    def __init__(self, path):

        # Original source image.
        self.source = Image.open(path)

        # Working image, may be scaled.
        self.working = self.source

        self.workingScale = 1.0;

    # Scale the original image to the passed width and store it as the working
    # image.
    def ScaleToWidth(self, width):

        # Calculate scale to maintain aspect ratio.
        scale = width / float(self.source.size[0])

        # Calculate new dimensions.
        dimensions = UnImage.ScaleDimensions(self.source.size, scale)

        # Scale the image.
        self.working = self.source.resize(dimensions, Image.LANCZOS)

        # Set working scale.
        self.workingScale = scale

    # Test to see if the working image contains the passed image.
    def ContainsImage(self, image):

        # Ensure test image is the same size or smaller.
        if self.working.size[0] < image.working.size[0] \
            or self.working.size[1] < image.working.size[1]:
                print "Test image is too large."
                return

        # Resize images.
        targetSize = 600

        # Is this image larger than the target size?
        if self.source.size[0] > targetSize:

            # Perform resize.
            self.ScaleToWidth(targetSize)
            image.ScaleToWidth(int(image.source.size[0] * self.workingScale))

        # Save images for visual reference.
        self.working.save("smhost.jpg")
        image.working.save("smtest.jpg")

        # Same size, width used for both dimensions for a square sample.
        sampleSize = (int(round(self.working.size[0] * 0.05)),
            int(round(self.working.size[0] * 0.05)))


        # Make sample of test image.
        # Currently doesn't use sampling functions, just uses whole image.
        # testSample, sampleOrigin = UnImage.GetSample(image.working, sampleSize)

        # Temporary.
        testSample = image.working
        sampleSize = testSample.size
        sampleOrigin = (0,0)

        # Testing setup.
        bestPositions = []
        bestFullMatch = 0
        bestFullPosition = ()

        # Width loop with adjustment for sample size.
        for xDim in range(0, self.working.size[0] - sampleSize[0]):

            # percentComplete = int((100 * (x / float(parentImageSize[0] - sampleSize[0]))) / 2) + 1

            # sys.stdout.write("\r[{0}{1}] ParRes: {3}, Samples Matched: {2}".format("=" * percentComplete, "-" * (50 - percentComplete), len(bestSamplePositions), originalParent.size))
            # sys.stdout.flush()

            # Height loop with adjustment for sample size.
            for yDim in range(0, self.working.size[1] - sampleSize[1]):

                testPosition = (xDim, yDim)

                # print (testPosition)

                # Sample parent.
                hostSample = UnImage.SampleImage(self.working, sampleSize, testPosition)
                result = UnImage.QuickCompare(testSample, hostSample)

                # Above requirement?
                if result == 1:

                    # Add to samples.
                    bestPositions.append(testPosition)

        # Loop saved samples.
        for samPos in bestPositions:
            cropOrigin = (samPos[0] - sampleOrigin[0], samPos[1] - sampleOrigin[1])

            # Test full child.
            parentCrop = UnImage.SampleImage(self.working, image.working.size, cropOrigin)
            result, matches = UnImage.CompareImages(parentCrop, image.working)

            # Better than best?
            if matches > bestFullMatch:

                # Record new best.
                bestFullMatch = matches
                bestFullPosition = cropOrigin

        # Clean up a little.
        gc.collect()

        # Got a best match?
        if bestFullMatch > 0:

            bestFullMatchPer = (float(bestFullMatch) / (image.working.size[0] * image.working.size[1])) * 100
            cropOrigin = (math.trunc(bestFullPosition[0] / self.workingScale), math.trunc(bestFullPosition[1] / self.workingScale))
            cropSize = image.source.size

            return True, bestFullMatchPer, (float(bestFullPosition[0]) / float(self.working.size[0]), float(bestFullPosition[1]) / float(self.working.size[1]))

        return False, object, object
