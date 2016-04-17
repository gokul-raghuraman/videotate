from functools import partial
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
	def __init__(self, **kwargs):
		super(AnnotationItemWidget, self).__init__(**kwargs)
		self.size_hint = (1, None)
		self.size = (100, 80)
		self.padding = 10
		self.spacing = 5
		self.category = "<category>"
		self.id = "<id>"
		self.label = Label(text="%s %s" % (self.category, self.id))
		self.label.size_hint = (None, 1)
		self.label.size = (150, 100)
		self.add_widget(self.label)
		self.deleteButton = Button(text="Delete")
		self.deleteButton.size_hint = (None, 1)
		self.deleteButton.size = (150, 100)
		self.add_widget(self.deleteButton)

	def setCategory(self, category):
		self.category = category

	def setId(self, inputId):
		self.id = inputId

	def refreshLabel(self):
		self.label.text = "%s %s" % (self.category, self.id)


class AnnotationPanelWidget(ScrollView):
	def __init__(self, **kwargs):
		super(AnnotationPanelWidget, self).__init__(**kwargs)
		self.do_scroll_x = False
		self.effect_cls = DampedScrollEffect

		self.layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
		self.layout.bind(minimum_height=self.layout.setter('height'))

		self.add_widget(self.layout)
		

	def addAnnotationItem(self, category):
		annotationItemWidget = AnnotationItemWidget()
		annotationItemWidget.setCategory(category)

		# Find an available ID
		itemWidgetIdsForCategory = [itemWidget.id for itemWidget in self.layout.children 
			if itemWidget.category == category]

		newId = 1
		if len(itemWidgetIdsForCategory) > 0:
			while str(newId) in itemWidgetIdsForCategory:
				newId += 1

		annotationItemWidget.setId(str(newId))
		annotationItemWidget.refreshLabel()
		self.layout.add_widget(annotationItemWidget)
		return annotationItemWidget

class VideoWidget(BoxLayout):
	def __init__(self, **kwargs):
		super(VideoWidget, self).__init__(**kwargs)

		self.videoEventDispatcher = VideoEventDispatcher()
		self.videoEventDispatcher.bind(on_video_load=self.handleOnVideoLoad)
		self.videoEventDispatcher.bind(on_play=self.handleOnPlay)
		self.videoEventDispatcher.bind(on_pause=self.handleOnPause)

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

		#self.slider.bind(value=self.handleSliderDragged)

		self._videoPausedBySliderTouch=False
		self.add_widget(self.slider)

		self.controlWidget = ControlWidget(self.videoEventDispatcher)
		self.controlWidget.size_hint = (1, 0.1)
		self.add_widget(self.controlWidget)

		# Schedule Clocks
		self.scheduleClocks()

	def scheduleClocks(self):
		Clock.schedule_interval(self.scheduleUpdateFrameControl, 0.03)
		Clock.schedule_interval(self.scheduleUpdateSlider, 0.03)
		Clock.schedule_interval(self.scheduleUpdateAnnotationCanvas, 0.03)

	def unscheduleClocks(self):
		Clock.unschedule(self.scheduleUpdateFrameControl)
		Clock.unschedule(self.scheduleUpdateSlider)
		Clock.unschedule(self.scheduleUpdateAnnotationCanvas)

	def handleOnVideoLoad(self, obj, *args):
		selectedFile = args[0]

		self.videoCanvasWidget.frameWidget.source = selectedFile
		self.enablePlayButton()
		self.enableFrameControl()
		self.enableSlider()

	def handleOnPlay(self, obj, *args):
		self.videoCanvasWidget.frameWidget.state = 'play'
		self.scheduleClocks()

	def handleOnPause(self, obj, *args):
		self.videoCanvasWidget.frameWidget.state = 'pause'
		self.unscheduleClocks()

	def handleSliderPressed(self, obj, *args):
		# Pause the video
		if self.videoCanvasWidget.frameWidget.state == 'play':
			self.videoCanvasWidget.frameWidget.state = 'pause'
			self._videoPausedBySliderTouch = True
		self.unscheduleClocks()

	def handleSliderDragged(self, obj, *args):
		# Don't consider if mouse not over slider
		pos = args[0].pos
		if pos[1] > slider_y:
			return
		self.seekToSliderPosition()
		self.updateFrameControl()
		self.updateAnnotationCanvas()

	def handleSliderReleased(self, obj, *args):
		# Resume the video
		#self.seekToSliderPosition()
		if self._videoPausedBySliderTouch:
			self.videoCanvasWidget.frameWidget.state = 'play'
			self._videoPausedBySliderTouch = False
		self.scheduleClocks()

	def enablePlayButton(self):
		self.controlWidget.playPauseButton.disabled = False

	def enableFrameControl(self):
		self.controlWidget.frameControl.disabled = False
		self.controlWidget.frameControl.text = '0'

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

	# Helper
	def _positionToFrame(self, position):
		return int(position * 24.0)

class ControlWidget(BoxLayout):

	def __init__(self, videoEventDispatcher, **kwargs):
		super(ControlWidget, self).__init__(**kwargs)
		
		self.padding = 20
		self.spacing = 20

		# Video playing flag. Important
		self.playing = False

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

		self.loadVideoButton = Button(text='Load Video')
		self.loadVideoButton.size_hint = (None, None)
		self.loadVideoButton.size = (200, 60)
		self.loadVideoButton.bind(on_release=self.openFileChooserPopup)

		self.add_widget(self.playPauseButton)
		self.add_widget(self.frameControl)
		self.add_widget(self.loadVideoButton)

		self.fileChooserPopup = Popup(title='Select Video File',
			content=FileChooserWindow(self.videoEventDispatcher),
			size_hint=(None, None), size=(1000, 1000))

	def openFileChooserPopup(self, obj):
		self.fileChooserPopup.open()

	def handleOnFileSelected(self, obj, *args):
		self.fileChooserPopup.dismiss()
		selectedFile = args[0]
		self.videoEventDispatcher.dispatchOnVideoLoad(selectedFile)

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
		if touch.y < slider_y:
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
				Color(1, 0, 0)
				# Redraw everything except the interacting annotation
				self.redrawCanvasAtFrame(excludeAnnotation=self.interactingAnnotation)
				# Render the interacting annotation separately
				point1 = Touch(self.interactingAnnotation.x1+touch.x-self.lastTouch.x, 
					self.interactingAnnotation.y1+touch.y-self.lastTouch.y)
				point2 = Touch(self.interactingAnnotation.x2+touch.x-self.lastTouch.x, 
					self.interactingAnnotation.y2+touch.y-self.lastTouch.y)
				self.drawRect(point1, point2)

		elif self.mode == MODE_CREATE:
			with self.canvas:
				Color(1, 0, 0)
				self.drawRect(self.lastTouch, touch)

	def on_touch_up(self, touch):
		if self.mouseDown is False:
			return
		self.redrawCanvasAtFrame()
		
		if self.mode == MODE_CREATE:

			self.point1 = Touch(self.lastTouch.x, self.lastTouch.y)
			self.point2 = Touch(touch.x, touch.y)
			self.mouseDown = False

			# Don't add annotation if rectangle is very tiny
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

		self.annotationManager.addAnnotationAtFrame(self.curFrame, 
			self.point1, self.point2, classLabel)
		self.point1 = Touch(-1, -1)
		self.point2 = Touch(-1, -1)
		self.redrawCanvasAtFrame()


	def drawRect(self, point1, point2):
		Line(points=[point1.x, point1.y, point2.x, point1.y, point2.x, point2.y, point1.x, point2.y, point1.x, point1.y], width=4)

	# TODO: This function will draw all existing ractangles (annotations)
	# for the current frame
	def redrawCanvasAtFrame(self, excludeAnnotation=None):
		self.canvas.clear()
		print("redrawing")
		# Get all annotations and interpolate as necessary
		annotationsForFrame = self.interpolator.getAnnotationsForFrame(self.curFrame)

		if excludeAnnotation:
			annotationsForFrame.remove(excludeAnnotation)

		with self.canvas:
			for annotation in annotationsForFrame:
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
		#self.canvasWidget.size = self.frameWidget.size
		self.add_widget(self.frameWidget)
		self.add_widget(self.canvasWidget)


class RootWidget(BoxLayout):
	def __init__(self, **kwargs):
		super(RootWidget, self).__init__(**kwargs)
		self.videoWidget = VideoWidget()
		self.videoWidget.size_hint = (0.7, 1)
		self.annotationPanelWidget = AnnotationPanelWidget()
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

