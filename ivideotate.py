from functools import partial
import cv2
import kivy
kivy.require('1.9.1')
from kivy.app import App
from kivy.graphics import Color
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.image import Image, AsyncImage
from kivy.uix.video import Video
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.clock import Clock

from filechooserwindow import FileChooserWindow
from videoeventdispatcher import VideoEventDispatcher
from videoformats import formats
from constants import *


class AnnotationPanelWidget(BoxLayout):
	def __init__(self, **kwargs):
		super(AnnotationPanelWidget, self).__init__(**kwargs)
		self.orientation = 'vertical'

class VideoWidget(BoxLayout):
	def __init__(self, **kwargs):
		super(VideoWidget, self).__init__(**kwargs)

		self.videoEventDispatcher = VideoEventDispatcher()
		self.videoEventDispatcher.bind(on_video_load=self.handleOnVideoLoad)
		self.videoEventDispatcher.bind(on_play=self.handleOnPlay)
		self.videoEventDispatcher.bind(on_pause=self.handleOnPause)

		self.orientation = 'vertical'
		canvasImagePath = PROJECT_DIR + 'canvas.jpg'
		self.frameWidget = Video(source=canvasImagePath)

		self.add_widget(self.frameWidget)

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
		Clock.schedule_interval(self.scheduleUpdateFrameControl, 0.03)
		Clock.schedule_interval(self.scheduleUpdateSlider, 0.03)

	def unscheduleClocks(self):
		Clock.unschedule(self.scheduleUpdateFrameControl)
		Clock.unschedule(self.scheduleUpdateSlider)

	def handleOnVideoLoad(self, obj, *args):
		selectedFile = args[0]
		# Compute frame count
		#cap = cv2.VideoCapture(selectedFile)
		#self.numFrames = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))

		self.frameWidget.source = selectedFile
		self.enablePlayButton()
		self.enableFrameControl()
		self.enableSlider()

	def handleOnPlay(self, obj, *args):
		self.frameWidget.state = 'play'

	def handleOnPause(self, obj, *args):
		self.frameWidget.state = 'pause'

	def handleSliderPressed(self, obj, *args):
		# Pause the video
		if self.frameWidget.state == 'play':
			self.frameWidget.state = 'pause'
			self._videoPausedBySliderTouch = True
		self.unscheduleClocks()

	def handleSliderDragged(self, obj, *args):
		self.seekToSliderPosition()
		self.updateFrameControl()

	def handleSliderReleased(self, obj, *args):
		# Resume the video
		#self.seekToSliderPosition()
		if self._videoPausedBySliderTouch:
			self.frameWidget.state = 'play'
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
		val = str(self._positionToFrame(self.frameWidget.position))
		self.controlWidget.frameControl.text = val

	def scheduleUpdateFrameControl(self, obj):
		if self.controlWidget.frameControl.disabled:
			return
		val = str(self._positionToFrame(self.frameWidget.position))
		self.controlWidget.frameControl.text = val

	def seekToSliderPosition(self):
		normValue = self.slider.value_normalized
		self.frameWidget.seek(normValue)

	def scheduleUpdateSlider(self, obj):
		if self.slider.disabled:
			return
		videoPosition = self.frameWidget.position
		videoDuration = self.frameWidget.duration
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

		self.fileChooserPopup = Popup(title='Test popup',
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




class RootWidget(BoxLayout):
	def __init__(self, **kwargs):
		super(RootWidget, self).__init__(**kwargs)
		self.videoWidget = VideoWidget()
		self.videoWidget.size_hint = (0.7, 1)
		self.annotationPanelWidget = AnnotationPanelWidget()
		self.annotationPanelWidget.size_hint = (0.3, 1)
		print(self.annotationPanelWidget.canvas)
		self.annotationPanelWidget.canvas.add(Color(1, 1, 1))
		self.add_widget(self.videoWidget)
		self.add_widget(self.annotationPanelWidget)

class IVideotate(App):

	def build(self):
		parent = RootWidget()
		return parent

if __name__ == '__main__':
	IVideotate().run()

