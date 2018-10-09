import os
import datetime
import xml.etree.ElementTree as ET
from .dfm import Grinder
import collections
import binascii

class DelphiProject:
    
    def __init__(self, path, name):
        # абсолютный путь к папке с проектом
        self.path = path
        self.forms = []
        self.date_update = None
        # абсолютный путь к файлу проекта
        self.path_to_dproj = None
        # проверить доступность папки
        if not os.path.exists(self.path):
            raise Exception("Не найдена папка с проектом "+self.path+".")
        # записать дату обновления
        self.date_update = datetime.datetime.fromtimestamp(os.path.getmtime(self.path))        
        # проверить доступность dproj
        dproj_count = 0
        for file in os.listdir(self.path):
            if file.endswith(".dproj"):
                if dproj_count > 0:
                    raise Exception("Найдено несколько файлов *.dproj для АРМа"  + name + ".")
                dproj_count += 1
                self.path_to_dproj = os.path.join(self.path, file)
        if dproj_count == 0:
            raise Exception("Файл проекта не найден для АРМа "+name)
    
    def read_dproj_file(self) -> None:
        """
        Парсит файл *.dproj, содержащий информацию о файлах проекта
        и заполняет список форм.
        """
        namespace = ""
        try:            
            root = ET.parse(self.path_to_dproj).getroot()
            if root.tag.startswith("{"):
                namespace = root.tag[:root.tag.find("}")+1]
            items = root.find(namespace + "ItemGroup")
            for item in items.findall(namespace+"DCCReference"):
                # имя модуля достаётся вот так, пока не востребовано
                module_name = item.attrib["Include"]
                # формируем абсолютный путь к файлу формы
                if len(item) > 0:
                    # form_path = os.path.join(self.path, item[0].text + ".dfm")
                    form_name = module_name[:module_name.find(".")]
                    form_path = os.path.join(self.path, form_name + ".dfm")
                    self.forms.append(form_path)
        except ET.ParseError:
            raise Exception("Не удалось распарсить файл проекта "+self.path_to_dproj)
        
    def get_forms(self) -> list:
        return self.forms


class DelphiForm:
    
    def __init__(self, path):
        self.path = path
        self.alias = None
        self.data = None
        if not os.path.exists(self.path):
            raise Exception("Файл формы " + self.path + " не найден.")
        self.date_update = datetime.datetime.fromtimestamp(os.path.getmtime(self.path))
    
    def read_dfm(self) -> None:
        grinder = Grinder()
        file = open(self.path, "rb")
        self.data = grinder.load_dfm(file.read())
        self.alias = self.data["name"]
        file.close()
    
    def get_db_components(self):
        """
        Генераторная функция, возвращающая компоненты для работы с БД,
        прикреплённые к форме
        """

        if self.data is None:
            self.read_dfm()
        
        for key in self.data:
            if DBComponent.is_db_component(self.data[key]):
                yield DBComponent.create(self.data[key], self.alias)

class DBComponent:

    def __init__(self, data, form_alias):
        self.name = data["name"]
        self.full_name = form_alias + "." + self.name
        self.type = data["type"]
    
    @classmethod
    def is_db_component(cls, something) -> bool:
        """
        Проверяет, является ли переданная структура данных описанием
        компонента для работы с БД.
        Признаки: 
        * это компонент (т.е. словарь с ключами name и type)
        * есть поле с именем, оканчивающимся на SQL.Strings или компонент принадлежит
          к классам TADOConnection или TADOStoredProc.
        """
        return (isinstance(something, dict)
            and ("name" in something)
            and ("type" in something)
            and (any(key.endswith("SQL.Strings") for key in something.keys())
                or something["type"] in ("TADOConnection", "TADOStoredProc")))

    @classmethod
    def create(classname, data, form_alias):
        if data["type"] == "TADOConnection":
            return DelphiConnection(data, form_alias)
        else:
            return DelphiQuery(data, form_alias)
        
    def __repr__(self):
        return self.name + ": " + self.type

    
class DelphiConnection(DBComponent):

    def __init__(self, data, form_alias):
        super(DelphiConnection, self).__init__(data, form_alias)
        self.database = ""
        # вытаскиваем имя базы данных из ConnectionString
        connection_args = "".join(data["ConnectionString"]).split(";")
        for arg in connection_args:
            if arg.startswith("Initial Catalog"):
                self.database = arg.split("=")[1].strip()
                break
        
    def __repr__(self):
        return self.full_name + ": TADOConnection; database: " + self.database

class DelphiQuery(DBComponent):

    def __init__(self, data, form_alias):
        super(DelphiQuery, self).__init__(data, form_alias)
        self.sql = ""
        self.connection = data.get("Connection", None)
        # если компонент - хранимая процедура, то текст запроса - название вызываемой процедуры
        if self.type == "TADOStoredProc":
            proc = data["ProcedureName"]
            self.sql = proc if proc.find(";") < 0 else proc[:proc.find(";")]
        else:
            # для остальных компонентов собираем текст запроса по частям
            # при этом каждый запрос компонента подписывается комментарием,
            # например, -- Insert.SQL.String
            query_strings = []
            for key in data:
                if key.endswith("SQL.Strings"):
                    query_strings.append("-- "+key+"\n")
                    query_strings.extend(data[key])
            self.sql = "\n".join(query_strings)
        # контрольная сумма по тексту запроса
        self.crc = binascii.crc32(self.sql.encode("utf-8"))
    
    
