class ClientProcedure(ClientQuery):
    procedure_name = Column(String(120), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "Компонент TADOStoredProc"
    }

    @property
    def sync_fields(self):
        return ["sql", "component_type", "crc32"]

    @classmethod
    def create_from(cls, original, parent):
        """
        Собирает ORM-модель для компонента TADOStoredProc.
        Исходные данные берутся из оригинального компонента с диска.

        Дата обновления ставится немножко костыльно, так как
        узнать реальную дату обновления компонента невозможно.
        """
        return ClientProcedure(
            name=original.name,
            procedure_name=original.procedure_name,
            component_type=original.type,
            last_update=datetime.datetime.now(),
            crc32=original.crc32,
            form=parent
        )