from functools import partial
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

		#for i in range(50):
		#	self.addAnnotationItem('dog')
		

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
		self.videoCanvasWidget = VideoCanvasWidget()

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

	def handleOnVideoLoad(self, obj, *args):
		selectedFile = args[0]
		# Compute frame count
		#cap = cv2.VideoCapture(selectedFile)
		#self.numFrames = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))

		self.videoCanvasWidget.frameWidget.source = selectedFile
		self.enablePlayButton()
		self.enableFrameControl()
		self.enableSlider()

	def handleOnPlay(self, obj, *args):
		self.videoCanvasWidget.frameWidget.state = 'play'

	def handleOnPause(self, obj, *args):
		self.videoCanvasWidget.frameWidget.state = 'pause'

	def handleSliderPressed(self, obj, *args):
		# Pause the video
		if self.videoCanvasWidget.frameWidget.state == 'play':
			self.videoCanvasWidget.frameWidget.state = 'pause'
			self._videoPausedBySliderTouch = True
		self.unscheduleClocks()

	def handleSliderDragged(self, obj, *args):
		print("Handling slider dragged")
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
		print("Updating frame control")
		if self.controlWidget.frameControl.disabled:
			return
		val = str(self._positionToFrame(self.videoCanvasWidget.frameWidget.position))
		self.controlWidget.frameControl.text = val

	def scheduleUpdateFrameControl(self, obj):
		#print("Schedule updating frame control")
		if self.controlWidget.frameControl.disabled:
			return
		val = str(self._positionToFrame(self.videoCanvasWidget.frameWidget.position))
		self.controlWidget.frameControl.text = val

	def updateAnnotationCanvas(self):
		self.videoCanvasWidget.canvasWidget.curFrame = \
		self._positionToFrame(self.videoCanvasWidget.frameWidget.position)

	def scheduleUpdateAnnotationCanvas(self, obj):
		self.videoCanvasWidget.canvasWidget.curFrame = \
		self._positionToFrame(self.videoCanvasWidget.frameWidget.position)		

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

		self.playPauseButton = Button(text='Play')
		self.playPauseButton.size_hint = (None, None)
		self.playPauseButton.size = (200, 60)
		self.playPauseButton.disabled = True
		self.playPauseButton.bind(on_release=self.handlePlayPauseClicked)

		self.frameControl = TextInput(text=' ')
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

	def handlePlayPauseClicked(self, obj):
		if self.playing:
			self.playPauseButton.text = 'Play'
			self.videoEventDispatcher.dispatchOnPause(None)
			self.playing = False
		else:
			self.playPauseButton.text = 'Pause'
			self.videoEventDispatcher.dispatchOnPlay(None)
			self.playing = True

class Touch:
	def __init__(self, x, y):
		self.x = x
		self.y = y

class AnnotationCanvasWidget(Widget):
	def __init__(self, **kwargs):
		super(AnnotationCanvasWidget, self).__init__(**kwargs)
		self.lastTouch = Touch(-1, -1)
		self.mouseDown = False

		# Important: we must receive the current frame number from
		# the videoWidget. This happens during
		self.curFrame = 0

	def on_touch_down(self, touch):
		if touch.y < 200:
			return
		self.lastTouch = Touch(touch.x, touch.y)
		self.mouseDown = True

		print("current frame = " + str(self.curFrame))

	def on_touch_move(self, touch):
		if self.mouseDown is False:
			return
		self.redrawCanvas()

		with self.canvas:
			self.drawRect(self.lastTouch, touch)

	def on_touch_up(self, touch):

		self.redrawCanvas()
		point1 = Touch(self.lastTouch.x, self.lastTouch.y)
		point2 = Touch(touch.x, touch.y)
		self.mouseDown = False


	def drawRect(self, point1, point2):
		Line(points=[point1.x, point1.y, point2.x, point1.y, point2.x, point2.y, point1.x, point2.y, point1.x, point1.y], width=4)

	# TODO: This function will draw all existing ractangles (annotations)
	# for the current frame
	def redrawCanvas(self):
		self.canvas.clear()

class VideoCanvasWidget(FloatLayout):
	def __init__(self, **kwargs):
		super(VideoCanvasWidget, self).__init__(**kwargs)

		self.frameWidget = Video(source=CANVAS_IMAGE_PATH)
		self.canvasWidget = AnnotationCanvasWidget()
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

	Window.size = (800, 600)

	IVideotate().run()

