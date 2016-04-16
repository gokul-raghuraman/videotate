import kivy
kivy.require('1.9.1')
from kivy.app import App
from random import random
# TODO: cleanup
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Line
#





class ImageWidget(Widget):
	def on_touch_down(self, touch):
		color = (random(), random(), random())
		with self.canvas:
			Color(*color)
			d = 30
			Ellipse(pos=(touch.x - d / 2, touch.y - d / 2), size=(d,d))
			touch.ud['line'] = Line(points=(touch.x, touch.y))

	def on_touch_move(self, touch):
		touch.ud['line'].points += [touch.x, touch.y]


class IVideotate(App):

	def build(self):
		parent = Widget()
		self.image = ImageWidget()
		clearButton = Button(text='Clear')
		clearButton.bind(on_release=self.clear_canvas)
		parent.add_widget(self.image)
		parent.add_widget(clearButton)
		return parent

	def clear_canvas(self, obj):
		print(obj)
		self.image.canvas.clear()

if __name__ == '__main__':
	IVideotate().run()