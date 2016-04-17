class Interpolator:
	def __init__(self, annotationManager):
		self.annotationManager = annotationManager

	def getAnnotationsForFrame(self):
		# Computes and returns all annotations

		annotationDict = self.annotationManager.getAnnotationDict()

		annotations = []
		for category in annotationDict:
			idFrameDict = annotationDict[category]