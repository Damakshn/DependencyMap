import re


class SQLProcessorMixin:
    """
    Миксин, приделывающий к классу приватный метод, подготавливающий
    поле sql для обработки поисковым запросом.
    """

    def clear_sql(self):
        """
        Обрабатывает свойство sql объекта и подготавливает его для
        обработки поисковым алгоритмом.

        Весь код приводится к нижнему регистру, удаляются комментарии,
        лишние пробелы и квадратные скобки; добавляется пробел после запятой.
        """

        def remove_comments(source: str) -> str:
            """
            Вспомогательная функция, удаляющая комментарии из sql.

            По факту, данный код не удаляет комментарии из текста,
            а вырезает текст вокруг комментариев, складывает его в список,
            который затем склеивается.

            При проходе по файлу функция также отслеживает и кавычки, чтобы
            не было ошибки при принятии /*, */ или -- в кавычках за комментарий.
            """
            # флаги, говорящие о том, что сейчас мы стоим внутри строчного
            # комментария или внутри строки в кавычках
            in_line = False
            in_string = False
            # уровень вложенности блочного комментария
            in_block = 0
            # позиция, с которой будет копироваться текст за пределами комментов
            start_pos = 0
            # буфер, в который мы будем класть куски текста за пределами комментариев
            chunks = []
            for pos in range(len(source)-1):
                if source[pos] == "'":
                    in_string = not (in_block or in_line) and not in_string
                elif source[pos] == "/" and source[pos+1] == "*":
                    # сочетание /* имеет значение, если ранее не была открыта
                    # строка или строчный комментарий
                    in_block = 0 if any([in_string, in_line]) else in_block + 1
                    # если это первый блочный комментарий, копируем в буфер весь текст до него
                    # если это уже не первое /*, то оно считается уже внутри того
                    # комментария, который был открыт первым
                    if in_block == 1:
                        chunks.append(source[start_pos:pos])
                elif source[pos] == "*" and source[pos+1] == "/":
                    # если нашлась закрывающая скобка блочного комментария, то
                    # уменьшаем уровень вложенности на 1;
                    # считается только та скобка, которая не закрыта кавычкой или
                    # строчным комментарием;
                    # если эта скобка - последняя, то смещаем start_pos к этому месту
                    # в тексте, чтобы при копировании перескочить комментарий
                    if in_block > 0 and all([not in_string, not in_line]):
                        in_block -= 1
                        if in_block == 0:
                            start_pos = pos + 2
                elif all([source[pos] == "-", source[pos+1] == "-", not in_line, not in_string, not in_block]):
                    # отлов строчного комментария - начало
                    in_line = True
                    chunks.append(source[start_pos:pos])
                elif source[pos] == "\n" and in_line:
                    # отлов строчного комментария - конец
                    in_line = False
                    start_pos = pos + 1
            # закидываем в буфер то, что осталось
            chunks.append(source[start_pos:len(source)])
            return "".join(chunks)

        # ----------- основная функция обработки sql -----------
        if not hasattr(self, "sql"):
            raise Exception(f"Класс {self.__class__.name} не имеет поля sql.")
        extra_spaces_and_line_breaks = r"\s+"
        # todo разобраться в lookahead
        comma_no_space = r"(?<=,)(?=[^\s])"
        square_brackets = r"[\[\]]"
        self.sql = remove_comments(self.sql.lower())
        self.sql = re.sub(extra_spaces_and_line_breaks, " ", self.sql)
        self.sql = re.sub(comma_no_space, " ", self.sql)
        self.sql = re.sub(square_brackets, "", self.sql)
