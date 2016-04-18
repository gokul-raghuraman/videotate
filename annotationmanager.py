import os
import json
from random import random


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
		annotation = None
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

		return annotation

	def updateAnnotationAtFrame(self, annotation, frame, point1, point2):

		print("GOING TO UPDATE ANNOTATION AT FRAME : " + str(frame))
		print(frame.__class__)
		print(annotation.id.__class__)
		print(self.annotationDict)

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
			print("UPDATING NEW ANNOT")
			color = frameDict[frameDict.keys()[0]].color
			frameDict[frame] = Annotation(point1.x, point1.y, point2.x, point2.y, annotation.category, annotation.id, color=color)
			idFrameDict[annotation.id] = frameDict
			self.annotationDict[annotation.category] = idFrameDict
		
		return

	def deleteAnnotation(self, category, idx):
		print("Before deleting annotation, dict is : " + str(self.annotationDict))
		idFrameDict = self.annotationDict[category]
		idFrameDict.pop(idx)
		if not idFrameDict:
			self.annotationDict.pop(category)

		print("After deleting annotation, dict is now : " + str(self.annotationDict))
		return

	def getWriteableAnnotations(self):
		writeableDict = {}
		for category in self.annotationDict:
			idFrameDict = {}
			for idx in self.annotationDict[category]:
				frameDict = {}
				for frame in self.annotationDict[category][idx]:
					annotation = self.annotationDict[category][idx][frame]
					annotationWriteable = [annotation.x1, annotation.y1, 
						annotation.x2, annotation.y2, annotation.category, 
							annotation.id, annotation.color]
					frameDict[frame] = annotationWriteable
				idFrameDict[idx] = frameDict
			writeableDict[category] = idFrameDict
		return writeableDict

	def getProcessedAnnotations(self, rawData):
		annotationDict = {}
		for category in rawData:
			idFrameDict = {}
			for idx in rawData[category]:
				frameDict = {}
				for frame in rawData[category][idx]:
					rawAnnotation = rawData[category][idx][frame]
					annotation = Annotation(rawAnnotation[0], rawAnnotation[1], 
						rawAnnotation[2], rawAnnotation[3], rawAnnotation[4], 
							rawAnnotation[5], color=(rawAnnotation[6][0], 
								rawAnnotation[6][1], rawAnnotation[6][2]))
					frameDict[int(frame)] = annotation
				idFrameDict[int(idx)] = frameDict
			annotationDict[category] = idFrameDict
		self.annotationDict = annotationDict

	def saveAnnotations(self, fileName):
		fileName = ''.join(fileName.split('.')[:-1]) + '.json'
		writeableDict = self.getWriteableAnnotations()
		with open(fileName, 'w') as fs:
			json.dump(writeableDict, fs)
		return

	def loadAnnotations(self, fileName):
		fileName = ''.join(fileName.split('.')[:-1]) + '.json'
		with open(fileName, 'r') as fs:
			rawData = json.load(fs)

		conditionedData = self.getProcessedAnnotations(rawData)


class Annotation:
	def __init__(self, x1, y1, x2, y2, category, idx, color=None):
		self.x1 = x1
		self.y1 = y1
		self.x2 = x2
		self.y2 = y2
		self.category = category
		self.id = idx

		# Assign a random color
		if color:
			self.color = color
		else:
			self.color = (random(), random(), random())