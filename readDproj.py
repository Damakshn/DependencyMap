from lxml import etree

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

