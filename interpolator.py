class Interpolator:
	def __init__(self, annotationManager):
		self.annotationManager = annotationManager

	def getAnnotationsForFrame(self, curFrame):
		# Computes and returns all annotations

		annotationDict = self.annotationManager.getAnnotationDict()

		print("GETTING INTERPOLATOR'S VERSION OF THE DICT : " ) 
		print(annotationDict)

		annotations = []
		print("INSIDE INTERPOLATOR, WORKING FOR FRAME : " + str(curFrame))
		for category in annotationDict:
			print("Looking at category : " + str(category))
			idFrameDict = annotationDict[category]
			for idx in idFrameDict:
				print("Looking at id : " + str(idx))
				frameAnnotationDict = idFrameDict[idx]
				prevFrame = None
				nextFrame = None
				for frame in sorted(frameAnnotationDict.keys()):
					print("Looking at frame : " + str(frame))
					#print("frame = " + str(frame))
					#print("curFrame = " + str(curFrame))
					if frame <= curFrame:
						print("Frame is less than or equal to curFrame...")
						prevFrame = frame
					if frame > curFrame:
						print("Frame is greater than curFrame...will assign and break")
						nextFrame = frame
						break

				# Now we have a few cases
				if prevFrame == curFrame:
					print("Now prevFrame equals curFrame!")
					# We don't have to compute anything, 
					# just return the annotation as is
					annotation = frameAnnotationDict[prevFrame]
					print("This is the annotation we want : " + str(annotation.x1) + ", " + str(annotation.y1) + ", " + str(annotation.x2) + ", " + str(annotation.y2))
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
					if prevFrame and nextFrame:
						# TODO: finish
						pass


		# TODO: Finish the other cases
		return annotations

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


