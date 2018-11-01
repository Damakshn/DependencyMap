import os
import datetime
import xml.etree.ElementTree as ET
from .dfm import Grinder
import collections
import binascii

class DelphiToolsException(Exception):
    pass

class DelphiProject:

    def __init__(self, path_to_dproj):
        self.forms = []
        self.last_update = None
        # абсолютный путь к файлу проекта
        self.path_to_dproj = path_to_dproj        
        # проверить доступность файла
        if not os.path.exists(self.path_to_dproj):
            raise DelphiToolsException(f"Не найден файл с проектом {self.path_to_dproj}.")
        # достаём путь к папке с проектом
        self.projdir = os.path.dirname(self.path_to_dproj)
        # запомнить дату обновления файла проекта
        self.last_update = datetime.datetime.fromtimestamp(os.path.getmtime(self.path_to_dproj))
        # читаем файл проекта (xml)
        namespace = ""
        try:
            root = ET.parse(self.path_to_dproj).getroot()
            if root.tag.startswith("{"):
                namespace = root.tag[:root.tag.find("}")+1]
            items = root.find(f"{namespace}ItemGroup")
            for item in items.findall(f"{namespace}DCCReference"):
                # имя модуля достаётся вот так, пока не востребовано
                module_name = item.attrib["Include"]
                # обрабатываем файл формы, если он указан
                if len(item) > 0:
                    form_name = module_name[:module_name.find(".")]
                    # формируем путь к файлу
                    form_path = os.path.join(self.projdir, f"{form_name}.dfm")
                    # проверяем доступность файла
                    if not os.path.exists(form_path):
                        raise DelphiToolsException(f"Файл с описанием формы {form_path} не найден")
                    form_update = datetime.datetime.fromtimestamp(os.path.getmtime(form_path))
                    # по максимальной среди форм дате обновления получаем дату обновления арма
                    if form_update > self.last_update:
                        self.last_update = form_update
                    self.forms.append({"name": form_name, "path" :form_path, "last_update": form_update})
        except ET.ParseError:
            raise DelphiToolsException(f"Не удалось распарсить файл проекта {self.path_to_dproj}")


class DelphiForm:

    def __init__(self, path):
        self.path = path
        # имя формы .дфм
        self.alias = None
        self.data = None
        if not os.path.exists(self.path):
            raise Exception(f"Файл формы {self.path} не найден.")
        self.last_update = datetime.datetime.fromtimestamp(os.path.getmtime(self.path))
    
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
        self.full_name = f"{form_alias}.{self.name}"
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
        return f"{self.full_name} : TADOConnection; database: {self.database}"

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
        self.crc32 = binascii.crc32(self.sql.encode("utf-8"))
    
    
