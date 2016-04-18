import math
from annotationmanager import Annotation

class Interpolator:
	def __init__(self, annotationManager):
		self.annotationManager = annotationManager
	
	# Computes and returns all annotations for the specified frame
	def getAnnotationsForFrame(self, curFrame):
		annotationDict = self.annotationManager.getAnnotationDict()
		annotations = []
		for category in annotationDict:
			idFrameDict = annotationDict[category]
			for idx in idFrameDict:
				frameAnnotationDict = idFrameDict[idx]
				prevFrame = None
				nextFrame = None
				for frame in sorted(frameAnnotationDict.keys()):
					if frame <= curFrame:
						prevFrame = frame
					if frame > curFrame:
						nextFrame = frame
						break

				# Now we have a few cases
				if prevFrame == curFrame:
					# We don't have to compute anything, 
					# just return the annotation as is
					annotation = frameAnnotationDict[prevFrame]
					annotations.append(annotation)

				else:
					# If prev frame exists but no next frame,
					# then use the same annotation as prevFrame's 
					# Do similarly if no previous frame exists, i.e. 
					# inherit nextFrame's annotation
					if prevFrame is not None and nextFrame is None:
						annotation = frameAnnotationDict[prevFrame]
						annotations.append(annotation)
					elif prevFrame is None and nextFrame is not None:
						annotation = frameAnnotationDict[nextFrame]
						annotations.append(annotation)

					# If annotations exist before and after, but not at
					# the current frame, then interpolate to get annotation
					if prevFrame is not None and nextFrame is not None:
						# We'll do a simple linear interpolation between the annotation
						# positions at prevFrame and nextFrame to get the interpolated
						# position at curFrame
						pAnnotation = frameAnnotationDict[prevFrame]
						nAnnotation = frameAnnotationDict[nextFrame]
						x1 = self.linInterp(prevFrame, nextFrame, curFrame, pAnnotation.x1, nAnnotation.x1)
						y1 = self.linInterp(prevFrame, nextFrame, curFrame, pAnnotation.y1, nAnnotation.y1)
						x2 = self.linInterp(prevFrame, nextFrame, curFrame, pAnnotation.x2, nAnnotation.x2)
						y2 = self.linInterp(prevFrame, nextFrame, curFrame, pAnnotation.y2, nAnnotation.y2)
						color = pAnnotation.color
						annotation = Annotation(x1, y1, x2, y2, pAnnotation.category, pAnnotation.id, color=color)
						annotations.append(annotation)

		return annotations

	# Linear interpolation function
	def linInterp(self, prevFrame, nextFrame, curFrame, prevFrameVal, nextFrameVal):
		curFrameVal = prevFrameVal + \
			((nextFrameVal - prevFrameVal) * (curFrame - prevFrame) 
				/ (nextFrame - prevFrame))
		return curFrameVal

	# Detects and returns the first annotation that fully
	# Contains the specified point
	def getContainingAnnotation(self, point, frame):
		annotationsForFrame = self.getAnnotationsForFrame(frame)

		for annotation in annotationsForFrame:
			x1 = annotation.x1
			x2 = annotation.x2
			y1 = annotation.y1
			y2 = annotation.y2

			if point.x < x1 or point.x < x2:
				if point.x > x2 or point.x > x1:
					if point.y < y1 or point.y < y2:
						if point.y > y2 or point.y > y1:
							return annotation

	# Detects and returns the first annotation whose
	# corner (any of four) is very close to specified point
	# Also returns the corner indexed in (intended) clockwise
	# order (0, 1, 2, 3) starting from (intended) top-left.
	def getCorneringAnnotationAndCorner(self, point, frame):
		annotationsForFrame = self.getAnnotationsForFrame(frame)
		distThreshold = 10
		for annotation in annotationsForFrame:
			x1 = annotation.x1
			x2 = annotation.x2
			y1 = annotation.y1
			y2 = annotation.y2

			corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
			for i in range(len(corners)):
				corner = corners[i]
				distToPoint = self.getDistBetweenPoints(corner, (point.x, point.y))
				if distToPoint < distThreshold:
					return (annotation, i)
		return (None, None)



	def getDistBetweenPoints(self, point1, point2):
		return math.sqrt(math.pow(point1[0] - point2[0], 2) + math.pow(point1[1] - point2[1], 2))



