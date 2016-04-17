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

	def getAnnotationDict(self, frame):
		return self.annotationDict

	# Function to add a new instance of any category. This will not
	# create a new keyframe annotation
	def addAnnotationAtFrame(self, frame, point1, point2, classLabel):
		annotation = Annotation(point1.x, point1.y, point2.x, point2.y, classLabel)
		
		# Get second level dict of {id : [Annotation(frame), ...]}
		idFrameDict = self.annotationDict.get(classLabel)
		if not idFrameDict:
			idFrameDict = {1 : {frame : annotation}}
			self.annotationDict[classLabel] = idFrameDict
		else:
			# Compute the smallest available id
			idsForCategory = sorted(idFrameDict.keys())
			newId = idsForCategory[0]
			while newId in idsForCategory:
				newId += 1
			frameDict = {frame : annotation}
			self.annotationDict[classLabel][newId] = frameDict

		return


class Annotation:
	def __init__(self, x1, y1, x2, y2, category):
		self.x1 = x1
		self.y1 = y1
		self.x2 = x2
		self.y2 = y2