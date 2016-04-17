from functools import partial
import kivy
kivy.require('1.9.1')
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.image import Image, AsyncImage
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup

from videoeventdispatcher import VideoEventDispatcher
from videoformats import formats
from constants import *

class FileChooserWindow(BoxLayout):
	def __init__(self, *args, **kwargs):
		super(FileChooserWindow, self).__init__(**kwargs)
		self.orientation = 'vertical'

		### Create event dispatcher instance
		self.videoEventDispatcher = args[0]

		# File chooser
		self.fileChooser = FileChooserIconView(path=ROOT_FILE_PATH)
		self.add_widget(self.fileChooser)

		# Buttons layout
		self.buttonsLayout = BoxLayout(orientation='horizontal', size_hint=[1, 0.1])
		self.openButton = Button(text='Open')
		self.openButton.bind(on_release=self.handleOpenButtonClick)
		self.buttonsLayout.add_widget(self.openButton)
		self.cancelButton = Button(text='Cancel')
		self.cancelButton.bind(on_release=self.handleCancelButtonclick)
		self.buttonsLayout.add_widget(self.cancelButton)
		self.add_widget(self.buttonsLayout)

	def handleOpenButtonClick(self, obj):
		if not self.fileChooser.selection:
			return
		selectedFile = self.fileChooser.selection[0]
		if selectedFile.split('.')[-1] not in formats:
			return

		# Valid video. Dispatch on_file_selected event 
		self.videoEventDispatcher.dispatchOnFileSelected(selectedFile)

	def handleCancelButtonclick(self, obj):
		self.videoEventDispatcher.dispatchOnPopupCancelled()




