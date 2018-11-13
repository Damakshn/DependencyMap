class SyncSummary:
    """
    Каталог синхронизируемых объектов.

    Используется как временный буфер, куда складываются будущие изменения.
    Объекты, попадая в каталог, делятся на 3 категории: создаваемые, удаляемые и обновляемые.

    Процесс синхронизации с исходниками сложен и подвержен ошибкам, поэтому необходим
    учёт всех изменений до того, как они записаны в базу; это позволяет управлять синхронизацией,
    останавливая её в случае ошибки или выводя пользователю предпреждающие сообщения.
    """
    def __init__(self):
        self.empty = True
        # Для раскладывания синхронизируемых объектов по категориям.
        self.update = {}
        self.delete = {}
        self.create = {}
        """
        При формировании каталога эти словари заполняются так:
            self.update = {"Form": [obj1, obj2], "Application": [obj3]}
            self.delete = {"ClientQuery": [obj4, obj5]}
            т.е. в качестве ключей словаря используются имена классов сохраняемых объектов.
        """
    
    def __save_to(self, category_name, obj):
        """
        Сохраняет объект в выбранную категорию.
        В качестве ключа используется имя класса сохраняемого объекта.
        Выделяет место внутри категории, если необходимо.
        """
        category = getattr(self, category_name)
        key = obj.__class__.__name__
        if key not in category:
            category[key] = []
        category[key].append(obj)
        

    def send_to_create(self, orm_object):
        """
        Помещает ORM-объект в каталог на вставку в таблицу базы данных.
        """
        self.__save_to("create", orm_object)
        self.empty = False

    def send_to_update(self, orm_object):
        """
        Помещает ORM-объект в каталог на обновление.
        """
        self.__save_to("update", orm_object)
        self.empty = False

    def send_to_delete(self, orm_object):
        """
        Помещает ORM-объект в каталог на удаление.
        """
        self.__save_to("delete", orm_object)
        self.empty = False
    
    def get_deleted_objects(self, cls):
        """
        Возвращает список объектов на удаление.

        Если указан класс, то список будет отфильтрован по этому классу.
        """
        return self.__get_objects_in_category("delete", cls)
    
    def get_updated_objects(self, cls):
        """
        Возвращает список объектов на обновление.

        Если указан класс, то список будет отфильтрован по этому классу.
        """
        return self.__get_objects_in_category("update", cls)
    
    def get_created_objects(self, cls):
        """
        Возвращает список объектов на создание.

        Если указан класс, то список будет отфильтрован по этому классу.
        """
        return self.__get_objects_in_category("create", cls)
    
    def get_persistent_objects(self, cls):
        """
        Возвращает список объектов на обновление и создание.

        Если указан класс, то список будет отфильтрован по этому классу.
        """
        updated = self.__get_objects_in_category("update", cls)
        created = self.__get_objects_in_category("create", cls)
        return created.extend(updated)
    
    def __get_objects_in_category(self, category_name, cls):
        """
        Возвращает список объектов из указанной категории.

        Если класс объектов не указан, то возвращает все объекты в категории,
        иначе - только объекты этого класса.
        """
        cls_name = cls.__name__
        category = getattr(self, category_name)
        if cls_name is None:
            return list(category.values())
        else:
            return category.setdefault(cls_name, [])

    @property
    def description(self):
        """
        Состав применяемых изменений - что будет создано/обновлено/удалено.
        """
        return f""

    def apply_changes(self, session):
        pass

    def merge_with(self, other):
        """
        Вливает в текущий каталог содержимое другого каталога.
        """
        for category in ["create", "update", "delete"]:
            other__category = getattr(other, category)
            self__category = getattr(self, category)
            for key in other__category:
                if key not in self__category:
                    self__category[key] = []
                self__category[key].extend(other__category[key])
