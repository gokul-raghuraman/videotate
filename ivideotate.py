from functools import partial
from random import random
import math
import cv2

import kivy
kivy.require('1.9.1')
from kivy.config import Config
from kivy.core.window import Window
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.image import Image, AsyncImage
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.effects.dampedscroll import DampedScrollEffect
from kivy.clock import Clock

from videocanvaswidget import VideoCanvasWidget
from filechooserwindow import FileChooserWindow
from videoeventdispatcher import VideoEventDispatcher
from annotationmanager import AnnotationManager, Annotation
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
		self.topWidget.deleteKeyButton.bind(on_release=self.handleDeleteKeyButtonPressed)
		self.bottomWidget = AnnotationItemWidgetBottom(key)
		self.bottomWidget.size_hint = (1, 0.5)
		self.add_widget(self.topWidget)
		self.add_widget(self.bottomWidget)

	def addKey(self, key):
		self.bottomWidget.addKey(key)
		self.refreshLabels()

	def removeKey(self, key):
		self.bottomWidget.removeKey(key)
		self.refreshLabels()

	def getKeys(self):
		return self.bottomWidget.keys

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

	def handleDeleteKeyButtonPressed(self, obj):
		deleteCategory = self.topWidget.category
		deleteId = int(self.topWidget.id)
		keys = [key for key in self.bottomWidget.keys]
		self.videoEventDispatcher.dispatchOnKeyDeleteRequest(deleteCategory, deleteId, keys)

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
		self.keysLabel.font_size = 15
		self.keysLabel.height = self.keysLabel.texture_size[1]
		self.add_widget(self.keysLabel)

	def addKey(self, key):
		if key in self.keys:
			return
		self.keys.append(key)
		self.keys = sorted(self.keys)

	def removeKey(self, key):
		self.keys.remove(key)
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
		self.deleteKeyButton = Button(text="Delete Key")
		self.deleteKeyButton.size_hint = (None, 1)
		self.deleteKeyButton.size = (150, 150)
		self.add_widget(self.deleteKeyButton)
		self.deleteButton = Button(text="Delete All")
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
		self.videoEventDispatcher.bind(on_key_delete=self.handleOnKeyDelete)

		self.layout = GridLayout(cols=1, spacing=50, size_hint_x=1, size_hint_y=None)
		self.layout.size = (100, 200)
		self.layout.padding = 10
		self.layout.bind(minimum_height=self.layout.setter('height'))

		self.add_widget(self.layout)

	def addAnnotationItem(self, annotation, frame):
		annotationItemWidget = AnnotationItemWidget(frame, self.videoEventDispatcher)
		annotationItemWidget.setCategory(annotation.category)
		annotationItemWidget.setId(str(annotation.id))
		annotationItemWidget.refreshLabels()
		self.layout.add_widget(annotationItemWidget)
		return annotationItemWidget

	def findItemWidgetForAnnotation(self, annotation):
		annotationItemWidgets = self.layout.children
		for itemWidget in annotationItemWidgets:
			if str(itemWidget.topWidget.category) == str(annotation.category) \
				and str(itemWidget.topWidget.id) == str(annotation.id):
				return itemWidget

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
						firstFrameAdded = True
		return

	def handleOnKeyDelete(self, obj, category, idx, frame):
		placeHolderAnnotation = Annotation(-1, -1, -1, -1, category, idx)
		widgetItemToUpdate = self.findItemWidgetForAnnotation(placeHolderAnnotation)
		widgetItemToUpdate.removeKey(frame)
		if len(widgetItemToUpdate.getKeys()) == 0:
			self.layout.remove_widget(widgetItemToUpdate)


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
		frameToSeek = args[0]
		self.unscheduleClocks()
		self.updateSliderToFrame(frameToSeek)
		self.seekToFrame(frameToSeek)

		# Forces an update to specified frame. Use with caution
		self.forceUpdateAnnotationCanvas(frameToSeek)

	def handleSliderReleased(self, obj, *args):
		# Resume the video
		pos = args[0].pos
		if pos[1] > slider_y_max or pos[1] < slider_y_min:
			return
		if self._videoPausedBySliderTouch:
			self.videoCanvasWidget.frameWidget.state = 'play'
			self._videoPausedBySliderTouch = False
			self.scheduleClocks()
		else:
			self.unscheduleClocks()

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

	def forceUpdateAnnotationCanvas(self, frame):
		self.videoCanvasWidget.canvasWidget.curFrame = frame
		self.videoCanvasWidget.canvasWidget.redrawCanvasAtFrame()

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

	def seekToFrame(self, frame):
		totalNumFrames = self._positionToFrame(self.videoCanvasWidget.frameWidget.duration)
		normValue = float(frame) / float(totalNumFrames)
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