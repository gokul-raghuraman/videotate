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
from kivy.event import EventDispatcher

class VideoEventDispatcher(EventDispatcher):
	def __init__(self, **kwargs):
		self.register_event_type('on_video_load')
		self.register_event_type('on_file_selected')
		self.register_event_type('on_play')
		self.register_event_type('on_pause')
		self.register_event_type('on_label_create')
		self.register_event_type('on_popup_cancelled')
		self.register_event_type('on_annotation_add')
		super(VideoEventDispatcher, self).__init__(**kwargs)

	def dispatchOnVideoLoad(self, value):
		self.dispatch('on_video_load', value)

	def dispatchOnFileSelected(self, value):
		self.dispatch('on_file_selected', value)

	def dispatchOnPlay(self, value):
		self.dispatch('on_play', value)

	def dispatchOnPause(self, value):
		self.dispatch('on_pause', value)

	def dispatchOnLabelCreate(self, value):
		self.dispatch('on_label_create', value)

	def dispatchOnPopupCancelled(self):
		self.dispatch('on_popup_cancelled')

	def dispatchOnAnnotationAdd(self, value):
		self.dispatch('on_annotation_add', value)

	def on_video_load(self, *args):
		print("Video Loaded")

	def on_file_selected(self, *args):
		print("File Selected")

	def on_play(self, *args):
		print("Video Playing")

	def on_pause(self, *args):
		print("Video Paused")

	def on_label_create(self, *args):
		print("Label Created")

	def on_popup_cancelled(self, *args):
		print("Popup Cancelled")

	def on_annotation_add(self, *args):
		print("Annotated Added")