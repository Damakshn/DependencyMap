import tkinter as tk
import tkinter.ttk as ttk


class DpmWidget:

    def __init__(self, owner, **kwargs):
        self._pane = tk.Frame(owner)

    def place(self, *args, **kwargs):
        x = kwargs["x"]
        y = kwargs["y"]
        self._pane.place(x=x, y=y)

    def pack(self, *args, **kwargs):
        self._pane.pack()

    def grid(self, *args, **kwargs):
        pass


class DpmGrid(DpmWidget):

    def __init__(self, owner, **kwargs):
        super().__init__(owner, **kwargs)

        self._default_cell_padding = 1
        self._columns = len(kwargs["columns"])
        self._rows = kwargs["rows"]
        self._columns_size = [c["width"] for c in kwargs["columns"]]
        self._column_headers = [c.get("header") for c in kwargs["columns"]]
        self._columns_editable = [c.get("editable",False) for c in kwargs["columns"]]
        self._cells = [[None] * self._columns] * (self._rows + 1)
        # заголовок
        for i in range(self._columns):
            header = tk.Label(self._pane, width=self._columns_size[i], text=self._column_headers[i], bg="white")
            self._locate_cell(header, i, 0)
        # остальные ячейки
        for i in range(1, self._rows + 1):
            for j in range(self._columns):
                if self._columns_editable[j]:
                    cell = tk.Entry(self._pane, width=self._columns_size[j])
                else:
                   cell = tk.Label(self._pane, width=self._columns_size[j], bg="white")
                self._locate_cell(cell, j, i)

    def _locate_cell(self, cell, x, y):
        setattr(cell, "x", x)
        setattr(cell, "y", y)
        setattr(cell, "mother", self)
        self._cells[y][x] = cell
        cell.grid(row=y, column=x, padx=self._default_cell_padding, pady=self._default_cell_padding)

    @property
    def columns(self):
        return self._columns

    @property
    def rows(self):
        return self._rows


def SayBoo(event):
    print("Booo!")

def test_grid():
    root = tk.Tk()
    main_frame = tk.Frame(root, height=800, width=850)
    columns = [
        {"width": 20, "header": "First"},
        {"width": 20, "header": "Second"},
        {"width": 20, "header": "Second"},
    ]
    g = DpmGrid(main_frame, columns=columns, rows=5)
    main_frame.pack()
    g.place(x=0, y=0)
    root.mainloop()

def start():
    root = tk.Tk()
    main_frame = tk.Frame(root, height=800, width=850, bg = 'green')
    main_frame.pack()

    # label
    label = tk.Label(main_frame, width=12, text="Это надпись")
    label.place(x=10, y=10)
    # entry
    entry = tk.Entry(main_frame, width=20)
    entry.insert(0, "text goes here")
    entry.place(x=10, y=40)
    # text
    txt = tk.Text(main_frame, height=5, width=100, wrap=tk.WORD)
    txt.insert(1.0, "Тут может быть много текста")
    txt.place(x=10, y=60)
    # listbox
    listbox = tk.Listbox(main_frame, height=3, width=5, selectmode=tk.SINGLE)
    choices = ["raz", "dva", "tri"]
    for choice in choices:
        listbox.insert(tk.END, choice)
    listbox.place(x=10, y=150)
    # combobox
    combo_items = ["raz", "dva", "tri"]
    combobox = ttk.Combobox(main_frame, values=combo_items, height=len(combo_items))
    combobox.set(combo_items[0])
    combobox.bind('<<ComboboxSelected>>', SayBoo)
    combobox.place(x=10, y=210)
    # Checkbutton
    # Scrollbar

    label.bind("<Button-3>", SayBoo)

    root.mainloop()


if __name__ == "__main__":
    # start()
    test_grid()
