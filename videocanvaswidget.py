import math

from kivy.uix.widget import Widget
from kivy.uix.video import Video
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color
from kivy.graphics.vertex_instructions import Line, Rectangle
from kivy.core.text import Label as CoreLabel

from annotationmanager import AnnotationManager
from interpolator import Interpolator
from constants import *


class VideoCanvasWidget(FloatLayout):
	def __init__(self, videoEventDispatcher, **kwargs):
		super(VideoCanvasWidget, self).__init__(**kwargs)
		self.videoEventDispatcher = videoEventDispatcher
		self.frameWidget = Video(source=CANVAS_IMAGE_PATH)
		self.canvasWidget = AnnotationCanvasWidget(self.videoEventDispatcher)
		self.add_widget(self.frameWidget)
		self.add_widget(self.canvasWidget)

class AnnotationCanvasWidget(Widget):
	def __init__(self, videoEventDispatcher, **kwargs):
		super(AnnotationCanvasWidget, self).__init__(**kwargs)

		self.videoEventDispatcher = videoEventDispatcher
		self.videoEventDispatcher.bind(on_label_create=self.handleOnLabelCreate)
		self.videoEventDispatcher.bind(on_annotation_delete=self.handleOnAnnotationDelete)
		self.videoEventDispatcher.bind(on_request_load_annotations=self.handleOnRequestLoadAnnotations)
		self.videoEventDispatcher.bind(on_request_save_annotations=self.handleOnRequestSaveAnnotations)
		self.videoEventDispatcher.bind(on_key_delete_request=self.handleOnKeyDeleteRequest)

		# Last touch point for anchoring current bounding box 
		# during mouse drag
		self.lastTouch = Touch(-1, -1)
		self.mouseDown = False

		# Active points for registering newly created bounding box
		self.point1 = Touch(-1, -1)
		self.point2 = Touch(-1, -1)

		# Annotation Manager
		self.annotationManager = AnnotationManager()

		# Interpolator
		self.interpolator = Interpolator(self.annotationManager)

		# Important: we must receive the current frame number from
		# the videoWidget. This happens during
		self.curFrame = 0

		# Interaction mode:
		# (1) Create bounding box
		# (2) Move bounding box
		# (3) Resize bounding box
		self.mode = MODE_CREATE

		# This is the annotation currently being interacted with
		# This is used in MODE_MOVE and MODE_RESIZE
		self.interactingAnnotation = None

		# Used for MODE_RESIZE
		self.interactingCornerIdx = None

	def on_touch_down(self, touch):
		# Don't consider if dragged over slider
		if touch.y < slider_y_max:
			return
		self.lastTouch = Touch(touch.x, touch.y)
		self.mouseDown = True

		# Compute mode for use in further interactions
		# If touch point fully within any existing bounding box, then
		# switch to MODE_MOVE
		containingAnnotation = self.getContainingAnnotation(touch)
		if containingAnnotation:
			self.interactingAnnotation = containingAnnotation
			self.mode = MODE_MOVE

		(corneringAnnotation, cornerIdx) = self.getCorneringAnnotationAndCorner(touch)
		if corneringAnnotation:
			self.interactingAnnotation = corneringAnnotation
			self.interactingCornerIdx = cornerIdx
			self.mode = MODE_RESIZE

	def on_touch_move(self, touch):
		if self.mouseDown is False:
			return
		self.redrawCanvasAtFrame()

		if self.mode == MODE_MOVE:
			with self.canvas:
				
				# Redraw everything except the interacting annotation
				self.redrawCanvasAtFrame(excludeAnnotation=self.interactingAnnotation)
				
				# Render the interacting annotation separately
				point1 = Touch(self.interactingAnnotation.x1+touch.x-self.lastTouch.x, 
					self.interactingAnnotation.y1+touch.y-self.lastTouch.y)
				point2 = Touch(self.interactingAnnotation.x2+touch.x-self.lastTouch.x, 
					self.interactingAnnotation.y2+touch.y-self.lastTouch.y)
				Color(*self.interactingAnnotation.color)
				self.drawRect(point1, point2)
				self.drawText2(point1, point2, self.interactingAnnotation.category, self.interactingAnnotation.id, self.interactingAnnotation.color)

		elif self.mode == MODE_RESIZE:
			with self.canvas:

				# Redraw everything except the interacting annotation
				self.redrawCanvasAtFrame(excludeAnnotation=self.interactingAnnotation)

				# Render the interacting annotation separately
				topLeft = Touch(self.interactingAnnotation.x1, self.interactingAnnotation.y1)
				bottomRight = Touch(self.interactingAnnotation.x2, self.interactingAnnotation.y2)

				if self.interactingCornerIdx == 0:
					topLeft = Touch(touch.x, touch.y)
				elif self.interactingCornerIdx == 1:
					bottomRight = Touch(touch.x, bottomRight.y)
					topLeft = Touch(topLeft.x, touch.y)
				elif self.interactingCornerIdx == 2:
					bottomRight = Touch(touch.x, touch.y)
				elif self.interactingCornerIdx == 3:
					topLeft = Touch(touch.x, topLeft.y)
					bottomRight = Touch(bottomRight.x, touch.y)
			
				Color(*self.interactingAnnotation.color)
				self.drawRect(topLeft, bottomRight)
				self.drawText2(topLeft, bottomRight, self.interactingAnnotation.category, self.interactingAnnotation.id, self.interactingAnnotation.color)

		elif self.mode == MODE_CREATE:
			with self.canvas:
				Color(1, 0, 0)
				self.drawRect(self.lastTouch, touch)

	def on_touch_up(self, touch):

		if self.mouseDown is False:
			return
		self.redrawCanvasAtFrame()
		
		if self.mode == MODE_MOVE:
			self.point1 = Touch(self.interactingAnnotation.x1+touch.x-self.lastTouch.x, 
					self.interactingAnnotation.y1+touch.y-self.lastTouch.y)
			self.point2 = Touch(self.interactingAnnotation.x2+touch.x-self.lastTouch.x, 
					self.interactingAnnotation.y2+touch.y-self.lastTouch.y)
			self.annotationManager.updateAnnotationAtFrame(self.interactingAnnotation, 
				self.curFrame, self.point1, self.point2)
			
			self.videoEventDispatcher.dispatchOnAnnotationUpdate(self.interactingAnnotation, self.curFrame)
			self.interactingAnnotation = None
			self.point1 = Touch(-1, -1)
			self.point2 = Touch(-1, -1)
			
			self.redrawCanvasAtFrame()

		elif self.mode == MODE_RESIZE:

			topLeft = Touch(self.interactingAnnotation.x1, self.interactingAnnotation.y1)
			bottomRight = Touch(self.interactingAnnotation.x2, self.interactingAnnotation.y2)

			if self.interactingCornerIdx == 0:
				topLeft = Touch(touch.x, touch.y)
			elif self.interactingCornerIdx == 1:
				bottomRight = Touch(touch.x, bottomRight.y)
				topLeft = Touch(topLeft.x, touch.y)
			elif self.interactingCornerIdx == 2:
				bottomRight = Touch(touch.x, touch.y)
			elif self.interactingCornerIdx == 3:
				topLeft = Touch(touch.x, topLeft.y)
				bottomRight = Touch(bottomRight.x, touch.y)

			self.point1 = topLeft
			self.point2 = bottomRight
			self.annotationManager.updateAnnotationAtFrame(self.interactingAnnotation, 
				self.curFrame, self.point1, self.point2)

			self.videoEventDispatcher.dispatchOnAnnotationUpdate(self.interactingAnnotation, self.curFrame)
			self.interactingAnnotation = None
			self.interactingCornerIdx = None
			self.point1 = Touch(-1, -1)
			self.point2 = Touch(-1, -1)
			self.redrawCanvasAtFrame()

		elif self.mode == MODE_CREATE:
			self.point1 = Touch(self.lastTouch.x, self.lastTouch.y)
			self.point2 = Touch(touch.x, touch.y)
			self.mouseDown = False

			# Don't add annotation if released over slider
			if touch.y < slider_y_max:
				return

			# Or if rectangle is very tiny
			if math.sqrt(math.pow(self.point1.x - self.point2.x, 2) + 
				math.pow(self.point1.y - self.point2.y, 2)) < 10:
				return

			self.labelerPopup = Popup(title='Enter Class Label',
				content=AnnotationLabelPopup(self.videoEventDispatcher),
				size_hint=(None, None), size=(500, 300))

			self.labelerPopup.open()

		self.mode = MODE_CREATE

	def getContainingAnnotation(self, touch):
		annotation = self.interpolator.getContainingAnnotation(touch, self.curFrame)
		return annotation

	def getCorneringAnnotationAndCorner(self, touch):
		(annotation, cornerIdx) = self.interpolator.getCorneringAnnotationAndCorner(touch, self.curFrame)
		return (annotation, cornerIdx)

	def handleOnLabelCreate(self, obj, *args):
		self.labelerPopup.dismiss()

		if -1 in [self.point1.x, self.point1.y, self.point2.x, self.point2.y]:
			print("Invalid bounding box!")
			return
		classLabel = args[0]

		addedAnnotation = self.annotationManager.addAnnotationAtFrame(self.curFrame, 
			self.point1, self.point2, classLabel)
		self.point1 = Touch(-1, -1)
		self.point2 = Touch(-1, -1)
		self.redrawCanvasAtFrame()

		self.videoEventDispatcher.dispatchOnAnnotationAdd(addedAnnotation, self.curFrame)

	def handleOnAnnotationDelete(self, obj, category, idx):
		# Actually delete the annotation using annotation manager
		self.annotationManager.deleteAnnotation(category, idx)
		self.redrawCanvasAtFrame()

	def handleOnRequestLoadAnnotations(self, obj, *args):
		fileName = args[0]
		self.annotationManager.loadAnnotations(fileName)
		self.redrawCanvasAtFrame()
		self.videoEventDispatcher.dispatchOnLoadAnnotations(self.annotationManager.annotationDict)

	def handleOnRequestSaveAnnotations(self, obj, *args):
		fileName = args[0]
		self.annotationManager.saveAnnotations(fileName)

	def handleOnKeyDeleteRequest(self, obj, category, idx, keys):
		if not self.curFrame in keys:
			return

		self.annotationManager.deleteAnnotationAtFrame(category, idx, self.curFrame)
		self.videoEventDispatcher.dispatchOnKeyDelete(category, idx, self.curFrame)
		self.redrawCanvasAtFrame()

	def drawRect(self, point1, point2):
		Line(points=[point1.x, point1.y, point2.x, point1.y, point2.x, point2.y, point1.x, point2.y, point1.x, point1.y], width=4)

	def redrawCanvasAtFrame(self, excludeAnnotation=None):
		self.canvas.clear()
		# Get all annotations and interpolate as necessary
		annotationsForFrame = self.interpolator.getAnnotationsForFrame(self.curFrame)

		# We want to exclude rendering the existing annotation when the
		# user tries to move/resize it.
		# Important: we can't directly reference the excludeAnnotation
		# object for removal because getContainingAnnotation will 
		# create a new object for in-between frames. So compare category
		# and id for removal
		if excludeAnnotation:
			for annotation in annotationsForFrame:
				if annotation.category == excludeAnnotation.category and annotation.id == excludeAnnotation.id:
					annotationsForFrame.remove(annotation)
					break

		with self.canvas:
			for annotation in annotationsForFrame:
				Color(*annotation.color)
				self.drawBoundingBox(annotation)
				self.drawText(annotation)

	def drawText(self, annotation):
		Color(*annotation.color)

		# get min x and max y
		pos = (min(annotation.x1, annotation.x2), max(annotation.y1, annotation.y2))

		#pos = (annotation.x1, annotation.y1)
		text = "%s %s" % (annotation.category, annotation.id)
		label = CoreLabel(text=text, font_size=35)
		label.refresh()
		text = label.texture
		Rectangle(size=text.size, pos=pos, texture=text)

	def drawText2(self, point1, point2, category, idx, color):
		Color(*color)
		#pos = (point.x, point.y)
		# get min x and max y
		pos = (min(point1.x, point2.x), max(point1.y, point2.y))
		text = "%s %s" % (category, idx)
		label = CoreLabel(text=text, font_size=35)
		label.refresh()
		text = label.texture
		Rectangle(size=text.size, pos=pos, texture=text)

	def drawBoundingBox(self, annotation):
		point1 = Touch(annotation.x1, annotation.y1)
		point2 = Touch(annotation.x2, annotation.y2)
		Line(points=[point1.x, point1.y, point2.x, point1.y, point2.x, point2.y, point1.x, point2.y, point1.x, point1.y], width=4)


class AnnotationLabelPopup(BoxLayout):
	def __init__(self, videoEventDispatcher, **kwargs):
		super(AnnotationLabelPopup, self).__init__(**kwargs)
		self.videoEventDispatcher = videoEventDispatcher
		self.orientation = 'vertical'
		self.spacing = 10
		self.padding = 10
		self.labelInput = TextInput(text='')
		self.labelInput.multiline = False
		self.labelInput.size_hint = (1, None)
		self.labelInput.size = (100, 60)
		self.createButton = Button(text='Create')
		self.createButton.size_hint = (None, None)
		self.createButton.size = (100, 60)
		self.createButton.bind(on_release=self.handleCreate)
		
		self.add_widget(self.labelInput)
		self.add_widget(self.createButton)

	def handleCreate(self, obj):
		if not self.labelInput.text:
			return
		self.videoEventDispatcher.dispatchOnLabelCreate(self.labelInput.text)


# Helper
class Touch:
	def __init__(self, x, y):
		self.x = x
		self.y = y