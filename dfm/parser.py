class Parser(object):

	def __init(self):
		self.state = self.parse_file
		self.current_event = None

	def check_event(self, choices*) -> Boolean:
		return True

	def get_event(self) -> Event:
		pass

	def parse_file(self) -> Event:
		return self.parse_object()

	def parse_object(self) -> Event:
		pass

	def parse_object_name(self) -> Event:
		pass

	def parse_object_type(self) -> Event:
		pass

	def parse_property_name(self) -> Event:
		pass

	def parse_object_property_value(self) -> Event:
		pass

	def parse_item_property_value(self) -> Event:
		pass

	def parse_item(self) -> Event:
		pass

	def parse_quoted_string(self) -> Event:
		pass

	def parse_value_sequence(self) -> Event:
		pass

	def parse_identifier_sequence(self) -> Event:
		pass

	def parse_item_sequence(self) -> Event:
		pass

	def parse_binary_sequence(self) -> Event:
		pass

