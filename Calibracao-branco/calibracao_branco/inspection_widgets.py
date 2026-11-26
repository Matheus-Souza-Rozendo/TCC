"""Peças visuais da IHM de classificação (Tkinter). Cada classe desenha uma parte da tela e só isso."""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List

from .inspection_session import InspectionRecord
from .tomato_inspection import SortingDestination, TomatoInspection

BACKGROUND = "#eceff1"
PANEL = "#ffffff"
HEADER = "#263238"
TEXT = "#212121"
MUTED = "#607d8b"
OK_COLOR = "#43a047"
WARNING_COLOR = "#fb8c00"
FONT = "Segoe UI"
MATURITY_TITLES = {"maduro": "Maduro", "intermediario": "Intermediário", "imaturo": "Imaturo", "sem LUT": "sem LUT"}


def number_text(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def light_tint(color_hex: str) -> str:
    """Cor bem clara do destino, para o fundo das linhas da tabela."""
    red, green, blue = (int(color_hex[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(255 - (255 - c) * 0.18):02x}" for c in (red, green, blue))


class StatusPill(tk.Label):
    """Indicador no cabeçalho: bolinha verde = pronto, laranja = falta algo."""

    def __init__(self, parent: tk.Widget, text: str):
        super().__init__(parent, text=f"●  {text}", bg=HEADER, fg=OK_COLOR, font=(FONT, 10, "bold"), padx=10)

    def set_ready(self, is_ready: bool) -> None:
        self.configure(fg=OK_COLOR if is_ready else WARNING_COLOR)


class PercentBar(tk.Canvas):
    def __init__(self, parent: tk.Widget, color_hex: str):
        super().__init__(parent, width=150, height=10, bg="#e0e0e0", highlightthickness=0)
        self._color_hex = color_hex

    def show(self, fraction: float) -> None:
        self.delete("all")
        self.create_rectangle(0, 0, round(150 * max(0.0, min(1.0, fraction))), 10, fill=self._color_hex, width=0)


class ResultCard(tk.Frame):
    """Cartão de um tomate: faixa na cor do destino, destino em destaque e as medidas."""

    def __init__(self, parent: tk.Widget, inspection: TomatoInspection):
        super().__init__(parent, bg=PANEL, highlightbackground="#cfd8dc", highlightthickness=1)
        destination = inspection.destination()
        tk.Frame(self, bg=destination.color_hex, width=8).pack(side="left", fill="y")
        body = tk.Frame(self, bg=PANEL, padx=10, pady=6)
        body.pack(side="left", fill="both", expand=True)
        title = tk.Frame(body, bg=PANEL)
        title.pack(fill="x")
        tk.Label(title, text=f" {inspection.number} ", bg=destination.color_hex, fg="white",
                 font=(FONT, 12, "bold")).pack(side="left")
        tk.Label(title, text=destination.title.upper(), bg=PANEL, fg=destination.color_hex,
                 font=(FONT, 15, "bold"), padx=8).pack(side="left")
        self._add_maturity(body, inspection)
        self._add_row(body, "Defeito", self._defect_text(inspection))
        size = inspection.size
        self._add_row(body, "Diâmetro", f"{number_text(size.diameter_mm)} mm")
        self._add_row(body, "Compr. × larg.", f"{number_text(size.length_mm)} × {number_text(size.width_mm)} mm")
        self._add_row(body, "Circularidade", number_text(size.circularity, 2))

    def _add_maturity(self, body: tk.Frame, inspection: TomatoInspection) -> None:
        maturity = inspection.maturity
        text = MATURITY_TITLES[maturity.label()]
        if maturity.is_evaluated:
            text += f"  ({number_text(100 * maturity.surface.red_fraction, 0)}% vermelho)"
        row = self._add_row(body, "Maturação", text)
        if maturity.is_evaluated:
            bar = PercentBar(row, SortingDestination.MADURO.color_hex)
            bar.grid(row=1, column=1, sticky="w", pady=(0, 2))
            bar.show(maturity.surface.red_fraction)

    @staticmethod
    def _defect_text(inspection: TomatoInspection) -> str:
        verdict = inspection.defect
        if not verdict.is_evaluated:
            return "sem CNN"
        return f"{verdict.label().capitalize()}  ({number_text(100 * verdict.confidence(), 0)}% de certeza)"

    @staticmethod
    def _add_row(body: tk.Frame, name: str, value: str) -> tk.Frame:
        row = tk.Frame(body, bg=PANEL)
        row.pack(fill="x")
        tk.Label(row, text=name, bg=PANEL, fg=MUTED, font=(FONT, 10), width=13, anchor="w").grid(row=0, column=0,
                                                                                                 sticky="w")
        tk.Label(row, text=value, bg=PANEL, fg=TEXT, font=(FONT, 10, "bold"), anchor="w").grid(row=0, column=1,
                                                                                               sticky="w")
        return row


class CounterTiles(tk.Frame):
    """Uma "placa" por destino com a contagem da sessão, em grade de 3 colunas."""

    COLUMNS = 3

    def __init__(self, parent: tk.Widget):
        super().__init__(parent, bg=PANEL)
        self._values: Dict[str, tk.Label] = {}
        tiles = [("Total", HEADER)] + [(d.title, d.color_hex) for d in SortingDestination]
        for index, tile in enumerate(tiles):
            self._add_tile(tile, divmod(index, self.COLUMNS))
        for column in range(self.COLUMNS):
            self.columnconfigure(column, weight=1, uniform="tiles")

    def show(self, counts: Dict[SortingDestination, int]) -> None:
        self._values["Total"].configure(text=str(sum(counts.values())))
        for destination, count in counts.items():
            self._values[destination.title].configure(text=str(count))

    def _add_tile(self, title_and_color, row_and_column) -> None:
        title, color_hex = title_and_color
        row, column = row_and_column
        tile = tk.Frame(self, bg=color_hex, pady=3)
        tile.grid(row=row, column=column, sticky="nsew", padx=2, pady=2)
        self._values[title] = tk.Label(tile, text="0", bg=color_hex, fg="white", font=(FONT, 16, "bold"))
        self._values[title].pack()
        tk.Label(tile, text=title, bg=color_hex, fg="white", font=(FONT, 9)).pack()


class HistoryTable(ttk.Frame):
    COLUMNS = [("hora", "Hora", 70), ("tomate", "Nº", 40), ("destino", "Destino", 100), ("maturacao", "Maturação", 100),
               ("vermelho", "% verm.", 65), ("defeito", "Defeito", 95), ("prob", "P(defeito)", 75),
               ("diametro", "Diâm. (mm)", 80), ("dimensoes", "C × L (mm)", 100), ("circularidade", "Circ.", 55)]

    def __init__(self, parent: tk.Widget, height_rows: int):
        super().__init__(parent)
        self._tree = ttk.Treeview(self, columns=[key for key, _, _ in self.COLUMNS], show="headings",
                                  height=height_rows)
        for key, title, width in self.COLUMNS:
            self._tree.heading(key, text=title)
            self._tree.column(key, width=width, anchor="center", stretch=True)
        for destination in SortingDestination:
            self._tree.tag_configure(destination.name, background=light_tint(destination.color_hex))
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def add(self, records: List[InspectionRecord]) -> None:
        # Mais recente em cima: é o que o operador está olhando.
        for record in reversed(records):
            self._tree.insert("", 0, values=self._values_of(record), tags=(record.inspection.destination().name,))

    def clear(self) -> None:
        self._tree.delete(*self._tree.get_children())

    def row_count(self) -> int:
        return len(self._tree.get_children())

    @staticmethod
    def _values_of(record: InspectionRecord) -> list:
        inspection = record.inspection
        size = inspection.size
        defect = inspection.defect
        return [record.timestamp.strftime("%H:%M:%S"), f"{record.round_number}.{inspection.number}",
                inspection.destination().title, MATURITY_TITLES[inspection.maturity.label()],
                number_text(100 * inspection.maturity.surface.red_fraction, 0) if inspection.maturity.is_evaluated
                else "-", defect.label(), number_text(defect.defect_probability, 2) if defect.is_evaluated else "-",
                number_text(size.diameter_mm), f"{number_text(size.length_mm)} × {number_text(size.width_mm)}",
                number_text(size.circularity, 2)]
