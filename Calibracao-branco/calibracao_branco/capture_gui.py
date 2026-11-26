"""Janela de captura do dataset próprio: python -m calibracao_branco.capture_gui --help

Câmera ao vivo à esquerda; à direita o destino (cor, defeitos ou teste), o número
do tomate, os rótulos e o botão "Tirar foto" (ou barra de espaço).
"""

import argparse
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, List

import cv2
import numpy as np

from .camera import FrameSource, OpenCvCameraAdapter, average_frames, parse_camera_address
from .capture_controller import CaptureController, LabelChoice
from .capture_destinations import ALL_DESTINATIONS
from .errors import CalibrationError
from .gain_file import GainFileReader
from .labeled_capture import DEFECTS
from .region import RegionOfInterest
from .scale_overlay import draw_region

FRAMES_PER_PHOTO = 3
REFRESH_INTERVAL_MS = 15
SCREEN_MARGIN_PX = 60
TASKBAR_AND_TITLE_PX = 80
MINIMUM_VIDEO_WIDTH = 320
NOT_INFORMED = ""
MATURITY_OPTIONS = [(NOT_INFORMED, "Não informar"), ("imaturo", "Imaturo (verde)"),
                    ("intermediario", "Intermediário (de vez)"), ("maduro", "Maduro")]
DEFECT_TITLES = {"rachado": "Rachado", "podre": "Podre / mofado", "dano_mecanico": "Dano mecânico", "mancha": "Mancha"}


class CameraFeed:
    """Imagem da câmera para a tela (com a região marcada) e para a foto (limpa, média de quadros)."""

    def __init__(self, camera: FrameSource, region: RegionOfInterest):
        self._camera = camera
        self._region = region

    def preview(self, display_width: int) -> np.ndarray:
        frame = draw_region(self._camera.read_frame(), self._region)
        scale = display_width / frame.shape[1]
        return cv2.resize(frame, (display_width, round(frame.shape[0] * scale)), interpolation=cv2.INTER_AREA)

    def photo(self) -> np.ndarray:
        return average_frames(self._camera, FRAMES_PER_PHOTO)


class CaptureWindow:
    def __init__(self, feed: CameraFeed, controller: CaptureController, display_width: int = 960):
        self._feed = feed
        self._controller = controller
        self._display_width = display_width
        self._root = tk.Tk()
        self._root.title("Captura do dataset - tomates")
        self._destination_index = tk.IntVar(value=0)
        self._maturity = tk.StringVar(value=NOT_INFORMED)
        self._defects: Dict[str, tk.BooleanVar] = {defect: tk.BooleanVar(value=False) for defect in DEFECTS}
        self._diameter = tk.StringVar(value="")
        self._label_widgets: List[tk.Widget] = []
        self._build_layout()
        self._display_width = self._video_width_that_fits(display_width)
        self._root.bind("<space>", self._on_space)
        self._root.protocol("WM_DELETE_WINDOW", self._root.destroy)
        self._refresh_status()

    def run(self) -> None:
        self._root.after(REFRESH_INTERVAL_MS, self._refresh_video)
        self._root.mainloop()

    def _build_layout(self) -> None:
        self._video = ttk.Label(self._root)
        self._video.grid(row=0, column=0, padx=8, pady=8, sticky="n")
        self._panel = ttk.Frame(self._root, padding=8)
        self._panel.grid(row=0, column=1, sticky="n")
        # "Tirar foto" logo abaixo do número do tomate: em tela pequena, ele nunca fica escondido embaixo.
        self._build_destination(self._panel)
        self._build_tomato_box(self._panel)
        self._build_photo_button(self._panel)
        labels_row = ttk.Frame(self._panel)
        labels_row.pack(fill="x")
        self._build_maturity(labels_row)
        self._build_defects(labels_row)
        self._build_diameter(self._panel)
        ttk.Button(self._panel, text="Sair", command=self._root.destroy).pack(anchor="e", pady=(10, 0))

    def _video_width_that_fits(self, requested_width: int) -> int:
        """Encolhe o vídeo se a tela for pequena; a altura segue a proporção 16:9 do DroidCam."""
        self._root.update_idletasks()
        free_width = self._root.winfo_screenwidth() - self._panel.winfo_reqwidth() - SCREEN_MARGIN_PX
        free_height = self._root.winfo_screenheight() - SCREEN_MARGIN_PX - TASKBAR_AND_TITLE_PX
        fits_on_screen = min(free_width, round(free_height * 16 / 9))
        return min(requested_width, max(MINIMUM_VIDEO_WIDTH, fits_on_screen))

    def _build_destination(self, panel: ttk.Frame) -> None:
        box = ttk.LabelFrame(panel, text="Destino das fotos", padding=6)
        box.pack(fill="x", pady=4)
        for index, destination in enumerate(ALL_DESTINATIONS):
            button = ttk.Radiobutton(box, text=f"{destination.title}  →  {destination.folder_name}",
                                     variable=self._destination_index, value=index, command=self._on_destination)
            button.pack(anchor="w")
            self._label_widgets.append(button)

    def _build_tomato_box(self, panel: ttk.Frame) -> None:
        box = ttk.LabelFrame(panel, text="Tomate", padding=6)
        box.pack(fill="x", pady=4)
        self._tomato_text = ttk.Label(box, font=("Segoe UI", 16, "bold"))
        self._tomato_text.pack(anchor="w")
        self._photos_text = ttk.Label(box)
        self._photos_text.pack(anchor="w")
        ttk.Button(box, text="Novo tomate", command=self._on_new_tomato).pack(anchor="w", pady=(4, 0))

    def _build_maturity(self, row: ttk.Frame) -> None:
        box = ttk.LabelFrame(row, text="Maturação", padding=6)
        box.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=4)
        for value, text in MATURITY_OPTIONS:
            button = ttk.Radiobutton(box, text=text, variable=self._maturity, value=value)
            button.pack(anchor="w")
            self._label_widgets.append(button)

    def _build_defects(self, row: ttk.Frame) -> None:
        box = ttk.LabelFrame(row, text="Defeitos (nenhum = sadio)", padding=6)
        box.grid(row=0, column=1, sticky="nsew", pady=4)
        for defect in DEFECTS:
            button = ttk.Checkbutton(box, text=DEFECT_TITLES[defect], variable=self._defects[defect])
            button.pack(anchor="w")
            self._label_widgets.append(button)

    def _build_diameter(self, panel: ttk.Frame) -> None:
        box = ttk.LabelFrame(panel, text="Diâmetro no paquímetro (mm, opcional)", padding=6)
        box.pack(fill="x", pady=4)
        entry = ttk.Entry(box, textvariable=self._diameter, width=10)
        entry.pack(anchor="w")
        self._label_widgets.append(entry)

    def _build_photo_button(self, panel: ttk.Frame) -> None:
        ttk.Style().configure("Photo.TButton", font=("Segoe UI", 14, "bold"), padding=10)
        ttk.Button(panel, text="📷  Tirar foto  (Espaço)", style="Photo.TButton",
                   command=self._on_take_photo).pack(fill="x", pady=(6, 2))
        self._status = ttk.Label(panel, wraplength=360, foreground="#1a5e20")
        self._status.pack(fill="x", pady=(0, 4))

    def _on_destination(self) -> None:
        try:
            self._controller.select_destination(ALL_DESTINATIONS[self._destination_index.get()])
        except ValueError as error:
            self._show_error(str(error))
        self._refresh_status()

    def _on_new_tomato(self) -> None:
        self._controller.start_new_tomato()
        self._maturity.set(NOT_INFORMED)
        for variable in self._defects.values():
            variable.set(False)
        self._diameter.set("")
        self._set_labels_enabled(True)
        self._refresh_status()

    def _on_space(self, event: tk.Event) -> None:
        if not isinstance(event.widget, (tk.Entry, ttk.Entry)):
            self._on_take_photo()

    def _on_take_photo(self) -> None:
        try:
            saved = self._controller.take_photo(self._feed.photo(), self._label_choice())
        except (ValueError, CalibrationError) as error:
            self._show_error(str(error))
            return
        self._set_labels_enabled(False)
        relative = saved.relative_to(self._controller.dataset_folder())
        self._status.configure(text=f"Foto salva: {relative.as_posix()}", foreground="#1a5e20")
        self._refresh_status()

    def _refresh_video(self) -> None:
        try:
            rgb = cv2.cvtColor(self._feed.preview(self._display_width), cv2.COLOR_BGR2RGB)
        except CalibrationError as error:
            messagebox.showerror("Câmera", str(error))
            self._root.destroy()
            return
        height, width = rgb.shape[:2]
        # PPM em memória: o Tk mostra direto, sem depender do Pillow.
        self._frame_image = tk.PhotoImage(data=f"P6 {width} {height} 255 ".encode() + rgb.tobytes(), format="PPM")
        self._video.configure(image=self._frame_image)
        self._root.after(REFRESH_INTERVAL_MS, self._refresh_video)


    def _label_choice(self) -> LabelChoice:
        return LabelChoice(
            defects=frozenset(defect for defect, variable in self._defects.items() if variable.get()),
            maturity=self._maturity.get() or None,
            diameter_text=self._diameter.get(),
        )

    def _set_labels_enabled(self, enabled: bool) -> None:
        for widget in self._label_widgets:
            widget.state(["!disabled"] if enabled else ["disabled"])

    def _refresh_status(self) -> None:
        controller = self._controller
        self._destination_index.set(ALL_DESTINATIONS.index(controller.destination))
        self._tomato_text.configure(text=f"Tomate nº {controller.tomato_id}")
        lock_note = "  (rótulos travados até 'Novo tomate')" if controller.is_locked else ""
        self._photos_text.configure(text=f"Fotos deste tomate: {controller.photos_of_tomato}{lock_note}")

    def _show_error(self, message: str) -> None:
        self._status.configure(text=message, foreground="#b00020")


def main(arguments: List[str] = None) -> int:
    options = _build_parser().parse_args(arguments)
    try:
        gain_file = Path(options.gain)
        region = GainFileReader().read_region(gain_file)
        camera_address = options.camera or GainFileReader().read_camera_address(gain_file)
        with OpenCvCameraAdapter(parse_camera_address(camera_address)) as camera:
            CaptureWindow(CameraFeed(camera, region), CaptureController(Path(options.raiz)),
                          options.largura_janela).run()
    except (CalibrationError, ValueError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m calibracao_branco.capture_gui",
                                     description="Janela de captura de fotos de tomates com rótulos.")
    parser.add_argument("--gain", default="bancada.gain", help="De onde vem a região de interesse e a câmera.")
    parser.add_argument("--camera", default="", help="Índice ou URL. Sem ela, usa a câmera gravada no .gain.")
    parser.add_argument("--raiz", default="..", help="Pasta onde ficam Dataset-cor, Dataset-proprio e Dataset-teste.")
    parser.add_argument("--largura-janela", type=int, default=960, help="Largura do vídeo na janela.")
    return parser


if __name__ == "__main__":
    sys.exit(main())
