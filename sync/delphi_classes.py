import os
import datetime
import xml.etree.ElementTree as ET
from dfm import DFMLoader, DFMException
import binascii
from .common_classes import Original
from .mixins import SQLProcessorMixin
import logging

class DelphiToolsException(Exception):
    pass


class DelphiProject(Original):

    def __init__(self, path_to_dproj):
        logging.info(f"Обрабатываем оригинал проекта {path_to_dproj}")
        self.forms = {}
        self.last_update = None
        # абсолютный путь к файлу проекта
        self.path = path_to_dproj
        # проверить доступность файла
        if not os.path.exists(self.path):
            msg = f"Не найден файл с проектом {self.path}"
            logging.error(msg)
            raise DelphiToolsException(msg)
        # достаём путь к папке с проектом
        self.projdir = os.path.dirname(self.path)
        # запомнить дату обновления файла проекта
        self.last_update = datetime.datetime.fromtimestamp(os.path.getmtime(self.path))
        # читаем файл проекта (xml)
        namespace = ""
        try:
            logging.debug(f"Парсим файл проекта {path_to_dproj}")
            root = ET.parse(self.path).getroot()
            if root.tag.startswith("{"):
                namespace = root.tag[:root.tag.find("}")+1]
            items = root.find(f"{namespace}ItemGroup")
            logging.debug(f"Достаём формы проекта")
            no_errors = True
            for item in items.findall(f"{namespace}DCCReference"):
                # имя модуля достаётся вот так; пока не востребовано
                module_name = item.attrib["Include"]
                # обрабатываем файл формы, если он указан
                if len(item) > 0:
                    form_name = module_name[:module_name.find(".")]
                    logging.debug(f"Обрабатываем файл формы {form_name}")
                    form_path = os.path.join(self.projdir, f"{form_name}.dfm")
                    logging.debug(f"Путь к файлу формы {form_path}")
                    # проверяем доступность файла
                    # ToDo - починить пути к общим файлам форм в армах
                    if not os.path.exists(form_path):
                        no_errors = False
                        msg = f"Файл с описанием формы {form_path} не найден."
                        logging.error(msg)
                        #raise DelphiToolsException(msg)
                        continue
                    form_update = datetime.datetime.fromtimestamp(os.path.getmtime(form_path))
                    # по максимальной среди форм дате обновления получаем дату обновления арма
                    if form_update > self.last_update:
                        self.last_update = form_update
                    self.forms[form_path] = DelphiForm(form_path)
                    if no_errors:
                        logging.info(f"Обработка проекта {self.path} завершена, все файлы прочитаны")
                    else:
                        logging.info(f"Обработка проекта {self.path} завершена с ошибками")
        except ET.ParseError:
            msg = f"Не удалось распарсить файл проекта {self.path}"
            logging.error(msg)
            raise DelphiToolsException(msg)


class DelphiForm(Original):

    def __init__(self, path):
        logging.info(f"Обрабатываем оригинал формы {path}")
        self.path = path
        self.name = os.path.split(self.path)[1]
        self.alias = None
        self.data = None
        if not os.path.exists(self.path):
            msg = f"Файл формы {self.path} не найден"
            logging.error(msg)
            raise Exception(msg)
        self.last_update = datetime.datetime.fromtimestamp(os.path.getmtime(self.path))
        self.is_broken = False
        self.parsing_error_message = None
        self.components = []

    @property
    def connections(self):
        """
        Словарь соединений формы
        """
        return {c.name: c for c in self.components if isinstance(c, DelphiConnection)}

    @property
    def queries(self):
        """
        Словарь компонентов, содержащих запросы к БД.
        """
        return {c.name: c for c in self.components if isinstance(c, DelphiQuery)}
    
    def parse(self):
        logging.debug(f"Парсим форму {self.name}")
        try:
            loader = DFMLoader()
            file = open(self.path, "rb")
            self.data = loader.load_dfm(file.read())
            self.alias = self.data["name"]
            file.close()
        except DFMException as e:
                logging.error(f"Не удалось распарсить форму {self.name}, компоненты не читаются, ошибка - {e}")
                self.is_broken = True
                self.parsing_error_message = str(e)
        if not self.is_broken:
            logging.debug(f"Формируем список компонентов формы {self.name}")
            for key in self.data:
                if DBComponent.is_db_component(self.data[key]):
                    new_component = DBComponent.create(self.data[key], self.alias)
                    self.components.append(new_component)
                    logging.debug(f"Прочитан компонент {new_component}")


class DBComponent(Original):

    def __init__(self, data, form_alias):
        self.name = f"{form_alias}.{data['name']}"
        self.type = data["type"]

    @classmethod
    def is_db_component(cls, something) -> bool:
        """
        Проверяет, является ли переданная структура данных описанием
        компонента для работы с БД.
        Признаки:
        * это компонент (т.е. словарь с ключами name и type)
        * есть поле с именем, оканчивающимся на SQL.Strings или
          компонент принадлежит к классам TADOConnection или TADOStoredProc.
        """
        return (
            isinstance(something, dict) and
            ("name" in something) and
            ("type" in something) and (
                any(key.endswith("SQL.Strings") for key in something.keys()) or
                something["type"] in ("TADOConnection", "TADOStoredProc")
            ))

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
                # извлекаем имя базы из свойств компонента
                # если указано имя тестовой базы, то отрезаем _test в конце
                dbname = arg.split("=")[1].strip()
                #if dbname.endswith("_test"):
                #    dbname = dbname[:dbname.find("_test")]
                self.database = dbname
                break

    def __repr__(self):
        return f"{self.name} : TADOConnection; database: {self.database}"


class DelphiQuery(DBComponent, SQLProcessorMixin):
    """
    Класс, олицетворяющий компонент Delphi работающий с данными из базы (датасет).

    ToDo есть компоненты, у которых несколько полей с запросами; также компонент TADOStoredProc не имеет поля
    с текстом запроса.
    """
    def __init__(self, data, form_alias):
        super(DelphiQuery, self).__init__(data, form_alias)
        self.sql = ""
        self.connection = data.get("Connection", None)
        if self.connection and self.connection.find(".") == -1:
            self.connection = f"{form_alias}.{self.connection}"
        # если компонент - хранимая процедура, то текст запроса - название вызываемой процедуры
        if self.type == "TADOStoredProc":
            proc = data["ProcedureName"]
            self.sql = "exec " + (proc if proc.find(";") < 0 else proc[:proc.find(";")]) + " "
        else:
            # для остальных компонентов собираем текст запроса по частям
            # при этом каждый запрос компонента подписывается комментарием,
            # например, -- Insert.SQL.String
            query_strings = []
            for key in data:
                if key.endswith("SQL.Strings"):
                    query_strings.append("-- " + key + "\n")
                    query_strings.extend(data[key])
            self.sql = "\n".join(query_strings)
        # очищаем sql методом из миксина
        self.clear_sql()
        # контрольная сумма по тексту запроса
        self.crc32 = binascii.crc32(self.sql.encode("utf-8"))
