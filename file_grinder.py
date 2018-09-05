from lxml import etree

class SourceProcessingException(Exception):

	def __init__(self, exc, function):
		#super().__init__(message)
		if hasattr(exc, "message"):
			self.message = str(exc)
		else:
			self.message = str(exc)
		self.function = function


def read_dproj(path):
	"""Парсит файл *.dproj и извлекает имена упомянутых в нём модулей и форм."""	
	source = open(path, "rb")
	tree = etree.parse(source)
	root = tree.getroot()
	# достаём префикс пространства имён
	prefix = "{"+root.nsmap[None]+"}"	
	# составляем список модулей и форм проекта
	modules = []
	forms = []
	for module in root.find(prefix+"ItemGroup").iterfind(prefix+"DCCReference"):
		module_name = module.get("Include")
		modules.append(module_name)
		# если у модуля есть дочерний элемент "Form", то формируем имя файла формы, меняя расширение модуля с *.pas на *.dfm
		if module.find(prefix+"Form") is not None:
			forms.append(module_name[:len(module_name)-3]+"dfm")
	return {"modules": modules, "forms": forms}

def _delete_word_wraps_in_sql(source):
	"""
	Удаляет кривые переносы строк, которые рисует Delphi в поле SQL своих компонентов.
	"""
	try:
		pattern = b"' +\r\n"
		word_wrap_position = source.find(pattern)
		while word_wrap_position >= 0:
			quote_position = source[word_wrap_position+1:].find(b"'")
			source = source[:word_wrap_position]+source[word_wrap_position+quote_position+2:]
			word_wrap_position = source.find(pattern)		
	except Exception as e:
		raise SourceProcessingException(e, "_delete_word_wraps_in_sql")
	return source
		


def _decode_sharps(source):
	"""
	Исправляет перекодированные Delphi русские буквы.
	Delphi заменяет кириллические символы на #<код в utf-8>.
	"""
	try:
		digits = {ord(str(d)) for d in range(10)}
		sharp_position = source.find(b"#")
		while sharp_position >= 0:
			# ищем место, где кончается числовой код
			code_length = 0		
			while sharp_position+code_length+1<len(source) and source[sharp_position+code_length+1] in digits:
				code_length += 1
			# если за решёткой стоит числовой код, заменяем его на букву
			# иногда попадается что-то вроде create table #temp, поэтому проверка нужна
			if code_length > 0:
				char_to_insert = bytes(chr(int(source[sharp_position+1:sharp_position+code_length+1])), "utf-8")
				source = source[:sharp_position]+char_to_insert+source[sharp_position+code_length+1:]
			sharp_position = source.find(b"#", sharp_position+1)
	except Exception as e:
		raise SourceProcessingException(e, "_decode_sharps")
		
	return source

def _delete_blank_lines(source):
	try:
		whitespaces = (" ", "\t", "\0")
		prev_pos = -1
		end_of_line = 0
		current_pos = source.find(b"\r\n")
		while current_pos >= 0:
			if prev_pos == -1:
				prev_pos = current_pos
				current_pos = source.find(b"\r\n", current_pos+1)
				continue		
			line = source[prev_pos+2:current_pos]
			line_is_blank = True
			char = 0		
			while line_is_blank and char < len(line):
				if not (chr(line[char]) in whitespaces):				
					line_is_blank = False
				char += 1
			if line_is_blank:			
				source = source[:prev_pos]+source[current_pos:]
			prev_pos = current_pos
			current_pos = source.find(b"\r\n", current_pos+1)
	except Exception as e:
		raise SourceProcessingException(e, "_delete_blank_lines")
		
	return source

def _delete_commented_code(source, comment_pattern):
	try:
		comment_open, comment_close, inline_comment = comment_pattern	
		comment_start = source.find(comment_open)
		while comment_start >= 0:
			comment_end = source.find(comment_close, comment_start+2)
			if comment_end >= 0:
				source = source[:comment_start]+source[comment_end+2:]
			else:
				source = source[:comment_start]
			comment_start = source.find(comment_open, comment_start+2)

		comment_start = source.find(inline_comment)
		while comment_start >= 0:
			comment_end = source.find(b"\r\n", comment_start+2)
			source = source[:comment_start]+source[comment_end:]
			comment_start = source.find(inline_comment, comment_end)
	except Exception as e:
		raise SourceProcessingException(e, "_delete_blank_lines")		
	return source

def _delete_sql_comments(source):
	sql_comment_pattern = (b"/*", b"*/", b"--")
	return _delete_commented_code(source, sql_comment_pattern)

def _delete_pascal_comments(source):
	pascal_comment_pattern = (b"{", b"}", b"//")
	return _delete_commented_code(source, pascal_comment_pattern)

def _delete_passive_code(source):
	return source

def _read_dephi_form_file(path):	
	source = open(path, "rb").read()
	return _delete_blank_lines(
		_decode_sharps(
			_delete_word_wraps_in_sql(source)
		)
	)

def _read_dephi_source_file(path):
	source = open(path, "rb").read()
	return _delete_blank_lines(
		_delete_pascal_comments(
			_decode_sharps(source)
		)
	)

def grind(path):
	if path.endswith(".pas"):
		return _read_dephi_source_file(path)
	if path.endswith(".dfm"):
		return _read_dephi_form_file(path)
