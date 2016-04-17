class AnnotationManager:

	def __init__(self):
		self.annotationDict = {}
		"""
		{
			'<category1>' : {	
								<id1>  :  {
											<frame1>: <Annotation>, 
											<frame2>: <Annotation>,
											 ...
										  }
								<id2>  :  {
											<frame1>: <Annotation>, 
											<frame2>: <Annotation>, 
											...
										  }
								...
							},

			'<category1>' : {	
								<id1>  :  {
											<frame1>: <Annotation>, 
											<frame2>: <Annotation>, 
											...
										   }
								<id2>  :  {
											<frame1>: <Annotation>, 
											<frame2>: <Annotation>, 
											...
										  }
								...
							},
				...
		}
		"""

	def getAnnotationDict(self):
		return self.annotationDict

	# Function to add a new instance of any category. This will not
	# create a new keyframe annotation
	def addAnnotationAtFrame(self, frame, point1, point2, classLabel):
		
		# Get second level dict of {id : [Annotation(frame), ...]}
		idFrameDict = self.annotationDict.get(classLabel)
		if not idFrameDict:
			annotation = Annotation(point1.x, point1.y, point2.x, point2.y, classLabel, 1)
			idFrameDict = {1 : {frame : annotation}}
			self.annotationDict[classLabel] = idFrameDict
		else:
			# Compute the smallest available id
			idsForCategory = sorted(idFrameDict.keys())
			newId = idsForCategory[0]
			while newId in idsForCategory:
				newId += 1
			annotation = Annotation(point1.x, point1.y, point2.x, point2.y, classLabel, newId)
			frameDict = {frame : annotation}
			self.annotationDict[classLabel][newId] = frameDict

		return

	def updateAnnotationAtFrame(self, annotation, frame, point1, point2):
		print("Updating annotation : " + str(annotation.category) + " " + str(annotation.id) + " at frame " + str(frame))

		# Find the annotation framedict (there should be one)
		idFrameDict = self.annotationDict[annotation.category]
		frameDict = idFrameDict[annotation.id]

		# If there's an existing annotation for this frame already,
		# just update its parameters
		if frameDict.get(frame):
			existingAnnotation = frameDict[frame]
			existingAnnotation.x1 = point1.x
			existingAnnotation.y1 = point1.y
			existingAnnotation.x2 = point2.x
			existingAnnotation.y2 = point2.y
		
		# If not, create a new annotation for this frame
		else: 
			frameDict[frame] = Annotation(point1.x, point1.y, point2.x, point2.y, annotation.category, annotation.id)
			idFrameDict[annotation.id] = frameDict
			self.annotationDict[annotation.category] = idFrameDict
		
		return


class Annotation:
	def __init__(self, x1, y1, x2, y2, category, idx):
		self.x1 = x1
		self.y1 = y1
		self.x2 = x2
		self.y2 = y2
		self.category = category
		self.id = idx