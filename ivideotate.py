from functools import partial
from random import random
import math
import cv2
import kivy
kivy.require('1.9.1')
from kivy.config import Config
from kivy.core.window import Window
from kivy.app import App
from kivy.graphics import Color, Ellipse
from kivy.graphics.vertex_instructions import Line, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.image import Image, AsyncImage
from kivy.uix.video import Video
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.effects.dampedscroll import DampedScrollEffect
from kivy.clock import Clock

from filechooserwindow import FileChooserWindow
from videoeventdispatcher import VideoEventDispatcher
from annotationmanager import AnnotationManager
from interpolator import Interpolator
from videoformats import formats
from constants import *


class AnnotationItemWidget(BoxLayout):
	def __init__(self, key, videoEventDispatcher, **kwargs):
		super(AnnotationItemWidget, self).__init__(**kwargs)
		self.orientation = 'vertical'
		self.size_hint = (1, None)
		self.size = (100, 100)
		self.videoEventDispatcher = videoEventDispatcher
		self.topWidget = AnnotationItemWidgetTop()
		self.topWidget.size_hint = (1, 0.5)
		self.topWidget.deleteButton.bind(on_release=self.handleDeleteButtonPressed)
		self.bottomWidget = AnnotationItemWidgetBottom(key)
		self.bottomWidget.size_hint = (1, 0.5)
		self.add_widget(self.topWidget)
		self.add_widget(self.bottomWidget)

	def addKey(self, key):
		self.bottomWidget.addKey(key)
		self.refreshLabels()

	def setCategory(self, category):
		self.topWidget.category = category

	def setId(self, inputId):
		self.topWidget.id = inputId

	def refreshLabels(self):
		self.topWidget.label.text = "%s %s" % (self.topWidget.category, self.topWidget.id)
		self.bottomWidget.keysLabel.text = "Keys: %s" % (', '.join([str(key) for key in self.bottomWidget.keys]))

	def handleDeleteButtonPressed(self, obj):
		deleteCategory = self.topWidget.category
		deleteId = int(self.topWidget.id)
		self.videoEventDispatcher.dispatchOnItemDelete(deleteCategory, deleteId)

class AnnotationItemWidgetBottom(BoxLayout):
	def __init__(self, key, **kwargs):
		super(AnnotationItemWidgetBottom, self).__init__(**kwargs)
		self.size_hint = (1, 1)
		self.padding = 10
		self.spacing = 5
		self.keys = [key]
		self.keysLabel = Label(text="Keys: %s" % (', '.join([str(key) for key in self.keys])))
		self.keysLabel.size = (500, 100)
		self.keysLabel.text_size = self.keysLabel.width, None
		self.keysLabel.height = self.keysLabel.texture_size[1]
		self.add_widget(self.keysLabel)

	def addKey(self, key):
		if key in self.keys:
			return
		self.keys.append(key)
		self.keys = sorted(self.keys)

class AnnotationItemWidgetTop(BoxLayout):
	def __init__(self, **kwargs):
		super(AnnotationItemWidgetTop, self).__init__(**kwargs)
		#self.size_hint = (1, None)
		#self.size = (100, 120)
		self.padding = 5
		self.spacing = 10
		self.category = "<category>"
		self.id = "<id>"
		self.label = Label(text="[b]%s %s[/b]" % (self.category, self.id))
		self.label.size_hint = (None, 1)
		self.label.size = (250, 150)
		self.add_widget(self.label)
		self.deleteButton = Button(text="Delete")
		self.deleteButton.size_hint = (None, 1)
		self.deleteButton.size = (150, 150)
		self.add_widget(self.deleteButton)


class AnnotationPanelWidget(ScrollView):
	def __init__(self, videoEventDispatcher, **kwargs):
		super(AnnotationPanelWidget, self).__init__(**kwargs)
		self.do_scroll_x = False
		self.effect_cls = DampedScrollEffect

		self.videoEventDispatcher = videoEventDispatcher
		self.videoEventDispatcher.bind(on_annotation_add=self.handleOnAnnotationAdd)
		self.videoEventDispatcher.bind(on_annotation_update=self.handleOnAnnotationUpdate)
		self.videoEventDispatcher.bind(on_item_delete=self.handleOnItemDelete)
		self.videoEventDispatcher.bind(on_load_annotations=self.handleOnLoadAnnotations)

		self.layout = GridLayout(cols=1, spacing=50, size_hint_x=1, size_hint_y=None)
		self.layout.size = (100, 200)
		self.layout.bind(minimum_height=self.layout.setter('height'))

		self.add_widget(self.layout)
		

	def addAnnotationItem(self, annotation, frame):
		annotationItemWidget = AnnotationItemWidget(frame, self.videoEventDispatcher)
		annotationItemWidget.setCategory(annotation.category)
		annotationItemWidget.setId(str(annotation.id))
		annotationItemWidget.refreshLabels()
		self.layout.add_widget(annotationItemWidget)
		return annotationItemWidget

	def handleOnAnnotationAdd(self, obj, *args):
		addedAnnotation = args[0]
		addedFrame = args[1]
		addedItemWidget = self.addAnnotationItem(addedAnnotation, addedFrame)

	def handleOnItemDelete(self, obj, *args):
		deleteCategory = args[0]
		deleteId = args[1]
		itemDeleted = False
		for itemWidget in self.layout.children:
			if str(itemWidget.topWidget.category) == str(deleteCategory) \
				and str(itemWidget.topWidget.id) == str(deleteId):
				self.layout.remove_widget(itemWidget)
				itemDeleted = True
		if itemDeleted:
			self.videoEventDispatcher.dispatchOnAnnotationDelete(deleteCategory, deleteId)


	def findItemWidgetForAnnotation(self, annotation):
		print("FINDING ITEM WIDGET")
		print("This annotation: " + str(annotation.category) + str(annotation.id))
		annotationItemWidgets = self.layout.children
		for itemWidget in annotationItemWidgets:
			print("Looking at itemwidget: " + str(itemWidget.topWidget.category) + str(itemWidget.topWidget.id))
			if str(itemWidget.topWidget.category) == str(annotation.category) \
				and str(itemWidget.topWidget.id) == str(annotation.id):
				print("Returning widget")
				return itemWidget

	def handleOnAnnotationUpdate(self, obj, *args):
		updatedAnnotation = args[0]
		updatedFrame = args[1]
		widgetItemForAnnotation = self.findItemWidgetForAnnotation(updatedAnnotation)
		widgetItemForAnnotation.addKey(updatedFrame)

	def handleOnLoadAnnotations(self, obj, annotationDict):
		for category in annotationDict:
			idFrameDict = annotationDict[category]
			for idx in idFrameDict:
				frameDict = idFrameDict[idx]
				firstFrameAdded = False
				for frame in frameDict:
					annotation = frameDict[frame]
					if firstFrameAdded:
						self.handleOnAnnotationUpdate(None, annotation, frame)
					else:
						self.handleOnAnnotationAdd(None, annotation, frame)
		return

class VideoWidget(BoxLayout):
	def __init__(self, videoEventDispatcher, **kwargs):
		super(VideoWidget, self).__init__(**kwargs)

		self.videoEventDispatcher = videoEventDispatcher
		self.videoEventDispatcher.bind(on_video_load=self.handleOnVideoLoad)
		self.videoEventDispatcher.bind(on_play=self.handleOnPlay)
		self.videoEventDispatcher.bind(on_pause=self.handleOnPause)
		self.videoEventDispatcher.bind(on_frame_control_update=self.handleOnFrameControlUpdate)

		self.orientation = 'vertical'
		CANVAS_IMAGE_PATH = PROJECT_DIR + 'canvas.jpg'
		self.videoCanvasWidget = VideoCanvasWidget(self.videoEventDispatcher)

		self.add_widget(self.videoCanvasWidget)

		self.slider = Slider(min=0, max=100, value=0, size_hint=(1, None),
			size=(100, 50))
		self.slider.disabled = True
		self.slider.bind(on_touch_down=self.handleSliderPressed)
		self.slider.bind(on_touch_move=self.handleSliderDragged)
		self.slider.bind(on_touch_up=self.handleSliderReleased)

		self._videoPausedBySliderTouch=False
		self.add_widget(self.slider)

		self.controlWidget = ControlWidget(self.videoEventDispatcher)
		self.controlWidget.size_hint = (1, 0.1)
		self.add_widget(self.controlWidget)

		# Schedule Clocks
		self.scheduleClocks()

	def scheduleClocks(self):
		print("Clocks scheduled")
		Clock.schedule_interval(self.scheduleUpdateFrameControl, 0.03)
		Clock.schedule_interval(self.scheduleUpdateSlider, 0.03)
		Clock.schedule_interval(self.scheduleUpdateAnnotationCanvas, 0.03)

	def unscheduleClocks(self):
		print("Clocks unscheduled")
		Clock.unschedule(self.scheduleUpdateFrameControl)
		Clock.unschedule(self.scheduleUpdateSlider)
		Clock.unschedule(self.scheduleUpdateAnnotationCanvas)

	def handleOnVideoLoad(self, obj, *args):
		selectedFile = args[0]

		self.videoCanvasWidget.frameWidget.source = selectedFile
		self.enablePlayButton()
		self.enableFrameControl()
		self.enableButtons()
		self.enableSlider()

	def handleOnPlay(self, obj, *args):
		self.videoCanvasWidget.frameWidget.state = 'play'
		self.scheduleClocks()

	def handleOnPause(self, obj, *args):
		self.videoCanvasWidget.frameWidget.state = 'pause'
		self.unscheduleClocks()

	def handleSliderPressed(self, obj, *args):
		# Pause the video
		pos = args[0].pos
		if pos[1] > slider_y_max or pos[1] < slider_y_min:
			return
		print("slider pressed")
		if self.videoCanvasWidget.frameWidget.state == 'play':
			self.videoCanvasWidget.frameWidget.state = 'pause'
			self._videoPausedBySliderTouch = True
		self.unscheduleClocks()

	def handleSliderDragged(self, obj, *args):
		# Don't consider if mouse not over slider
		pos = args[0].pos
		if pos[1] > slider_y_max or pos[1] < slider_y_min:
			return

		self.seekToSliderPosition()
		self.updateFrameControl()
		self.updateAnnotationCanvas()

	def handleOnFrameControlUpdate(self, obj, *args):
		print("Frame control updated!!!!!!!")
		print(args)
		frameToSeek = args[0]
		self.updateSliderToFrame(frameToSeek)
		self.seekToSliderPosition()
		self.updateAnnotationCanvas()

	def handleSliderReleased(self, obj, *args):
		# Resume the video
		pos = args[0].pos
		if pos[1] > slider_y_max or pos[1] < slider_y_min:
			return
		if self._videoPausedBySliderTouch:
			self.videoCanvasWidget.frameWidget.state = 'play'
			self._videoPausedBySliderTouch = False
		self.scheduleClocks()

	def enablePlayButton(self):
		self.controlWidget.playPauseButton.disabled = False

	def enableFrameControl(self):
		self.controlWidget.frameControl.disabled = False
		self.controlWidget.frameControl.text = '0'

	def enableButtons(self):
		self.controlWidget.loadAnnotationsButton.disabled = False
		self.controlWidget.saveAnnotationsButton.disabled = False

	def enableSlider(self):
		self.slider.disabled = False

	def updateFrameControl(self):
		if self.controlWidget.frameControl.disabled:
			return
		val = str(self._positionToFrame(self.videoCanvasWidget.frameWidget.position))
		self.controlWidget.frameControl.text = val

	def scheduleUpdateFrameControl(self, obj):
		if self.controlWidget.frameControl.disabled:
			return
		val = str(self._positionToFrame(self.videoCanvasWidget.frameWidget.position))
		self.controlWidget.frameControl.text = val

	def updateAnnotationCanvas(self):
		self.videoCanvasWidget.canvasWidget.curFrame = \
		self._positionToFrame(self.videoCanvasWidget.frameWidget.position)
		self.videoCanvasWidget.canvasWidget.redrawCanvasAtFrame()

	def scheduleUpdateAnnotationCanvas(self, obj):
		self.videoCanvasWidget.canvasWidget.curFrame = \
		self._positionToFrame(self.videoCanvasWidget.frameWidget.position)		
		self.videoCanvasWidget.canvasWidget.redrawCanvasAtFrame()

	def seekToSliderPosition(self):
		normValue = self.slider.value_normalized
		self.videoCanvasWidget.frameWidget.seek(normValue)

	def scheduleUpdateSlider(self, obj):
		if self.slider.disabled:
			return
		videoPosition = self.videoCanvasWidget.frameWidget.position
		videoDuration = self.videoCanvasWidget.frameWidget.duration
		self.slider.value_normalized = videoPosition / videoDuration

	def updateSliderToFrame(self, frame):
		if self.slider.disabled:
			return
		videoPosition = self._frameToPosition(frame)
		videoDuration = self.videoCanvasWidget.frameWidget.duration
		self.slider.value_normalized = videoPosition / videoDuration

	# Helpers
	def _positionToFrame(self, position):
		return int(position * 24.0)

	def _frameToPosition(self, frame):
		return float(frame) / 24.0

class ControlWidget(BoxLayout):

	def __init__(self, videoEventDispatcher, **kwargs):
		super(ControlWidget, self).__init__(**kwargs)
		
		self.padding = 20
		self.spacing = 20

		# Video playing flag. Important
		self.playing = False
		self.activeFile = ""

		self.videoEventDispatcher = videoEventDispatcher
		self.videoEventDispatcher.bind(on_file_selected=self.handleOnFileSelected)
		self.videoEventDispatcher.bind(on_popup_cancelled=self.handleOnPopupCancelled)

		self.playPauseButton = Button(text='Play')
		self.playPauseButton.size_hint = (None, None)
		self.playPauseButton.size = (200, 60)
		self.playPauseButton.disabled = True
		self.playPauseButton.bind(on_release=self.handlePlayPauseClicked)

		self.frameControl = TextInput(text=' ')
		self.frameControl.multiline = False
		self.frameControl.size_hint = (None, None)
		self.frameControl.size = (120, 60)
		self.frameControl.disabled = True
		self.frameControl.bind(on_text_validate=self.handleFrameControlChanged)

		self.loadVideoButton = Button(text='Load Video')
		self.loadVideoButton.size_hint = (None, None)
		self.loadVideoButton.size = (200, 60)
		self.loadVideoButton.bind(on_release=self.openFileChooserPopup)

		self.loadAnnotationsButton = Button(text='Load Annotations')
		self.loadAnnotationsButton.size_hint = (None, None)
		self.loadAnnotationsButton.size = (250, 60)
		self.loadAnnotationsButton.disabled = True
		self.loadAnnotationsButton.bind(on_release=self.loadAnnotations)

		self.saveAnnotationsButton = Button(text='Save Annotations')
		self.saveAnnotationsButton.size_hint = (None, None)
		self.saveAnnotationsButton.size = (250, 60)
		self.saveAnnotationsButton.disabled = True
		self.saveAnnotationsButton.bind(on_release=self.saveAnnotations)


		self.add_widget(self.playPauseButton)
		self.add_widget(self.frameControl)
		self.add_widget(self.loadVideoButton)
		self.add_widget(self.loadAnnotationsButton)
		self.add_widget(self.saveAnnotationsButton)

		self.fileChooserPopup = Popup(title='Select Video File',
			content=FileChooserWindow(self.videoEventDispatcher),
			size_hint=(None, None), size=(1000, 1000))

	def openFileChooserPopup(self, obj):
		self.fileChooserPopup.open()

	def loadAnnotations(self, obj):
		if not self.activeFile:
			return
		self.videoEventDispatcher.dispatchOnRequestLoadAnnotations(self.activeFile)

	def saveAnnotations(self, obj):
		if not self.activeFile:
			return
		self.videoEventDispatcher.dispatchOnRequestSaveAnnotations(self.activeFile)

	def handleOnFileSelected(self, obj, *args):
		self.fileChooserPopup.dismiss()
		selectedFile = args[0]
		self.videoEventDispatcher.dispatchOnVideoLoad(selectedFile)
		self.activeFile = selectedFile

	def handleOnPopupCancelled(self, obj, *args):
		self.fileChooserPopup.dismiss()

	def handlePlayPauseClicked(self, obj):
		if self.playing:
			self.playPauseButton.text = 'Play'
			self.videoEventDispatcher.dispatchOnPause(None)
			self.playing = False
		else:
			self.playPauseButton.text = 'Pause'
			self.videoEventDispatcher.dispatchOnPlay(None)
			self.playing = True

	def handleFrameControlChanged(self, obj, *args):
		# Better way is to first check for valid input
		newFrame = 0
		try:
			newFrame = int(obj.text)
		except ValueError:
			return
		self.videoEventDispatcher.dispatchOnFrameControlUpdate(newFrame)



		

# Helper
class Touch:
	def __init__(self, x, y):
		self.x = x
		self.y = y

class AnnotationCanvasWidget(Widget):
	def __init__(self, videoEventDispatcher, **kwargs):
		super(AnnotationCanvasWidget, self).__init__(**kwargs)

		self.videoEventDispatcher = videoEventDispatcher
		self.videoEventDispatcher.bind(on_label_create=self.handleOnLabelCreate)
		self.videoEventDispatcher.bind(on_annotation_delete=self.handleOnAnnotationDelete)
		self.videoEventDispatcher.bind(on_request_load_annotations=self.handleOnRequestLoadAnnotations)
		self.videoEventDispatcher.bind(on_request_save_annotations=self.handleOnRequestSaveAnnotations)

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

	def on_touch_move(self, touch):
		if self.mouseDown is False:
			return
		self.redrawCanvasAtFrame()

		if self.mode == MODE_MOVE:
			with self.canvas:
				#Color(1, 0, 0)
				#Color(*self.interactingAnnotation.color)
				# Redraw everything except the interacting annotation
				self.redrawCanvasAtFrame(excludeAnnotation=self.interactingAnnotation)
				# Render the interacting annotation separately
				point1 = Touch(self.interactingAnnotation.x1+touch.x-self.lastTouch.x, 
					self.interactingAnnotation.y1+touch.y-self.lastTouch.y)
				point2 = Touch(self.interactingAnnotation.x2+touch.x-self.lastTouch.x, 
					self.interactingAnnotation.y2+touch.y-self.lastTouch.y)
				Color(*self.interactingAnnotation.color)
				self.drawRect(point1, point2)

		elif self.mode == MODE_CREATE:
			with self.canvas:
				Color(1, 0, 0)
				#Color(random(), random(), random())
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

	def handleOnRequestLoadAnnotations(self, obj, *args):
		print("On request load")
		fileName = args[0]
		self.annotationManager.loadAnnotations(fileName)
		self.redrawCanvasAtFrame()
		self.videoEventDispatcher.dispatchOnLoadAnnotations(self.annotationManager.annotationDict)

	def handleOnRequestSaveAnnotations(self, obj, *args):
		fileName = args[0]
		self.annotationManager.saveAnnotations(fileName)

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

class VideoCanvasWidget(FloatLayout):
	def __init__(self, videoEventDispatcher, **kwargs):
		super(VideoCanvasWidget, self).__init__(**kwargs)

		self.videoEventDispatcher = videoEventDispatcher

		self.frameWidget = Video(source=CANVAS_IMAGE_PATH)
		self.canvasWidget = AnnotationCanvasWidget(self.videoEventDispatcher)
		self.add_widget(self.frameWidget)
		self.add_widget(self.canvasWidget)


class RootWidget(BoxLayout):
	def __init__(self, **kwargs):
		super(RootWidget, self).__init__(**kwargs)
		videoEventDispatcher = VideoEventDispatcher()
		self.videoWidget = VideoWidget(videoEventDispatcher)
		self.videoWidget.size_hint = (0.7, 1)
		self.annotationPanelWidget = AnnotationPanelWidget(videoEventDispatcher)
		self.annotationPanelWidget.size_hint = (0.3, 1)
		self.add_widget(self.videoWidget)
		self.add_widget(self.annotationPanelWidget)

class IVideotate(App):

	def build(self):
		parent = RootWidget()
		return parent

if __name__ == '__main__':

	Window.size = (1000, 800)

	IVideotate().run()

