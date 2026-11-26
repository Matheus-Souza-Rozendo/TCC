"""IHM de classificação de tomates cereja: python -m calibracao_branco.inspection_gui --help

Vídeo ao vivo da região de interesse; "Classificar" (ou Espaço) tira a foto
(média de 3 quadros), classifica cada tomate e registra no CSV do dia.
Com a classificação contínua ligada, o resultado aparece direto no vídeo.
"""

import argparse
import sys
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import List, Optional

import cv2
import numpy as np

from .camera import FrameSource, OpenCvCameraAdapter, average_frames, parse_camera_address
from .defect_classifier import MissingModelDefectClassifierNullObject, defect_classifier_for
from .errors import CalibrationError
from .gain_file import GainFileReader
from .image_files import load_image, save_image
from .inspection_overlay import InspectionOverlay
from .inspection_session import InspectionSession
from .inspection_widgets import (BACKGROUND, FONT, HEADER, MUTED, PANEL, CounterTiles, HistoryTable, ResultCard,
                                 StatusPill)
from .maturity_classifier import MissingLutMaturityClassifierNullObject, maturity_classifier_for
from .scale_file import ScaleSectionReader
from .tomato_inspection import InspectionModels, InspectionReport, TomatoInspectionFacade

FRAMES_PER_PHOTO = 3
REFRESH_INTERVAL_MS = 30
RESULT_HOLD_MS = 4000
CONTINUOUS_CARDS_INTERVAL_S = 0.7
MAXIMUM_CARDS = 2
SIDE_PANEL_WIDTH = 400  # em pixels de uma tela com escala 100%
MINIMUM_VIDEO_SIZE = (480, 300)


class StillImageFrameSource:
    """Uma foto fazendo o papel da câmera: para testar a IHM sem a bancada."""

    def __init__(self, image: np.ndarray):
        self._image = image

    def read_frame(self) -> np.ndarray:
        return self._image.copy()


@dataclass(frozen=True)
class InspectionSetup:
    facade: TomatoInspectionFacade
    session: InspectionSession
    has_lut: bool
    has_cnn: bool


class InspectionWindow:
    def __init__(self, camera: FrameSource, setup: InspectionSetup):
        self._camera = camera
        self._facade = setup.facade
        self._session = setup.session
        self._overlay = InspectionOverlay(setup.facade.region)
        self._held_result_until = 0.0
        self._last_cards_update = 0.0
        self._last_result_image: Optional[np.ndarray] = None
        self._root = tk.Tk()
        self._root.title("Classificador de tomate cereja")
        self._root.configure(bg=BACKGROUND)
        self._root.minsize(1100, 680)
        self._maximize()
        self._continuous = tk.BooleanVar(value=False)
        self._style()
        self._build_layout()
        self._video_area_size = MINIMUM_VIDEO_SIZE
        self._bind_keys()
        self._show_model_status(setup)

    @property
    def root(self) -> tk.Tk:
        return self._root

    def run(self) -> None:
        self._root.after(REFRESH_INTERVAL_MS, self._refresh_video)
        self._root.mainloop()

    def _show_model_status(self, setup: InspectionSetup) -> None:
        self._lut_pill.set_ready(setup.has_lut)
        self._cnn_pill.set_ready(setup.has_cnn)
        missing = [name for name, ready in (("LUT de cor", setup.has_lut), ("CNN de defeitos", setup.has_cnn))
                   if not ready]
        if missing:
            self._set_status(f"Atenção: sem {' e '.join(missing)} - essa parte aparece como 'sem LUT'/'sem CNN'.")

    # ----- montagem da tela -----

    def _style(self) -> None:
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure("Classify.TButton", font=(FONT, 16, "bold"), padding=14, foreground="white",
                        background="#1565c0", borderwidth=0)
        style.map("Classify.TButton", background=[("active", "#0d47a1"), ("pressed", "#0d47a1")])
        style.configure("Treeview", font=(FONT, 9), rowheight=22)
        style.configure("Treeview.Heading", font=(FONT, 9, "bold"))
        style.configure("Panel.TCheckbutton", background=PANEL, font=(FONT, 10))

    def _build_layout(self) -> None:
        self._build_header()
        # Rodapé antes do meio: o meio expande e, empacotado primeiro, espremeria a tabela.
        self._build_bottom()
        middle = tk.Frame(self._root, bg=BACKGROUND)
        middle.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        video_area = tk.Frame(middle, bg="black")
        video_area.pack(side="left", fill="both", expand=True)
        video_area.bind("<Configure>", self._on_video_area_resized)
        self._video = tk.Label(video_area, bg="black")
        self._video.place(relx=0.5, rely=0.5, anchor="center")
        self._mode_label = tk.Label(video_area, text="AO VIVO", bg="#c62828", fg="white", font=(FONT, 10, "bold"),
                                    padx=8)
        self._mode_label.place(x=10, y=10)
        self._build_side_panel(middle)

    def _build_header(self) -> None:
        header = tk.Frame(self._root, bg=HEADER, pady=8, padx=14)
        header.pack(fill="x")
        tk.Label(header, text="🍅  Classificador de Tomate Cereja", bg=HEADER, fg="white",
                 font=(FONT, 16, "bold")).pack(side="left")
        tk.Label(header, text="maturação (LUT)  ·  defeito (CNN)  ·  tamanho (mm)", bg=HEADER, fg="#b0bec5",
                 font=(FONT, 10)).pack(side="left", padx=16)
        self._cnn_pill = StatusPill(header, "CNN")
        self._cnn_pill.pack(side="right")
        self._lut_pill = StatusPill(header, "LUT")
        self._lut_pill.pack(side="right")
        StatusPill(header, "Câmera").pack(side="right")

    def _build_side_panel(self, parent: tk.Frame) -> None:
        # Largura fixa: o que sobrar da tela fica para o vídeo.
        panel = tk.Frame(parent, bg=PANEL, width=self._scaled(SIDE_PANEL_WIDTH), padx=12, pady=12)
        panel.pack(side="left", fill="y", padx=(10, 0))
        panel.pack_propagate(False)
        ttk.Button(panel, text="Classificar  (Espaço)", style="Classify.TButton",
                   command=self._on_classify).pack(fill="x")
        ttk.Checkbutton(panel, text="Classificação contínua no vídeo  (C)", variable=self._continuous,
                        style="Panel.TCheckbutton", command=self._on_continuous_toggled).pack(anchor="w", pady=(8, 4))
        buttons = tk.Frame(panel, bg=PANEL)
        buttons.pack(side="bottom", fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Salvar imagem", command=self._on_save_image).pack(side="left", expand=True, fill="x")
        ttk.Button(buttons, text="Zerar contagem", command=self._on_reset).pack(side="left", expand=True, fill="x",
                                                                               padx=(6, 0))
        self._counters = CounterTiles(panel)
        self._counters.pack(side="bottom", fill="x")
        tk.Label(panel, text="Contagem da sessão", bg=PANEL, fg=MUTED, font=(FONT, 10, "bold")).pack(
            side="bottom", anchor="w", pady=(6, 2))
        tk.Label(panel, text="Resultado", bg=PANEL, fg=MUTED, font=(FONT, 10, "bold")).pack(anchor="w", pady=(6, 2))
        self._cards = tk.Frame(panel, bg=PANEL)
        self._cards.pack(fill="both", expand=True)
        self._show_cards_message("Coloque os tomates na área amarela e clique em Classificar.")

    def _build_bottom(self) -> None:
        self._status = tk.Label(self._root, text=f"Registro do dia: {self._session.log_file}", bg="#cfd8dc",
                                fg=HEADER, font=(FONT, 9), anchor="w", padx=10)
        self._status.pack(fill="x", side="bottom")
        self._history = HistoryTable(self._root, height_rows=4)
        self._history.pack(fill="x", side="bottom", padx=10, pady=8)

    def _scaled(self, pixels_at_100_percent: int) -> int:
        """Larguras em pixels acompanham a escala do Windows, como as fontes (senão o texto corta)."""
        return round(pixels_at_100_percent * self._root.winfo_fpixels("1i") / 96)

    def _maximize(self) -> None:
        try:
            self._root.state("zoomed")
        except tk.TclError:
            # "zoomed" só existe no Windows; em outro sistema a janela abre no tamanho mínimo.
            pass

    def _bind_keys(self) -> None:
        self._root.bind("<space>", lambda event: self._on_classify())
        self._root.bind("<KeyPress-c>", lambda event: self._toggle_continuous())
        self._root.bind("<Escape>", lambda event: self._back_to_live())

    def _on_video_area_resized(self, event: tk.Event) -> None:
        # O vídeo ocupa o espaço que sobrar na janela (maximizada ou não, em qualquer tela).
        self._video_area_size = (max(MINIMUM_VIDEO_SIZE[0], event.width), max(MINIMUM_VIDEO_SIZE[1], event.height))

    # ----- ações -----

    def _on_classify(self) -> None:
        try:
            report = self._facade.inspect(average_frames(self._camera, FRAMES_PER_PHOTO))
        except CalibrationError as error:
            self._set_status(f"Erro: {str(error).splitlines()[0]}")
            return
        records = self._session.register(report)
        self._history.add(records)
        self._counters.show(self._session.counts)
        self._show_report(report)
        self._last_result_image = self._overlay.draw(report)
        self._held_result_until = time.monotonic() + RESULT_HOLD_MS / 1000
        self._show_image(self._last_result_image, "RESULTADO  (Esc = ao vivo)", "#1565c0")
        self._set_status(f"Classificação {self._session.round_number}: {len(report.tomatoes)} tomate(s) em "
                         f"{report.elapsed_ms:.0f} ms. Registro: {self._session.log_file}")

    def _on_continuous_toggled(self) -> None:
        self._held_result_until = 0.0

    def _toggle_continuous(self) -> None:
        self._continuous.set(not self._continuous.get())
        self._on_continuous_toggled()

    def _back_to_live(self) -> None:
        self._held_result_until = 0.0

    def _on_reset(self) -> None:
        self._session.reset_counts()
        self._history.clear()
        self._counters.show(self._session.counts)
        self._set_status("Contagem zerada (o CSV do dia continua com tudo).")

    def _on_save_image(self) -> None:
        if self._last_result_image is None:
            self._set_status("Classifique antes de salvar a imagem.")
            return
        destination = self._session.log_file.parent / "imagens" / f"resultado_{datetime.now():%Y%m%d_%H%M%S}.png"
        save_image(self._last_result_image, destination)
        self._set_status(f"Imagem salva: {destination}")

    # ----- vídeo -----

    def _refresh_video(self) -> None:
        try:
            if time.monotonic() >= self._held_result_until:
                self._show_live_frame(self._camera.read_frame())
        except CalibrationError as error:
            messagebox.showerror("Câmera", str(error))
            self._root.destroy()
            return
        self._root.after(REFRESH_INTERVAL_MS, self._refresh_video)

    def _show_live_frame(self, frame: np.ndarray) -> None:
        if not self._continuous.get():
            self._show_image(self._overlay.live_view(frame), "AO VIVO", "#c62828")
            return
        report = self._facade.inspect(frame)
        self._show_image(self._overlay.draw(report), f"CONTÍNUO  {report.elapsed_ms:.0f} ms", "#6a1b9a")
        if time.monotonic() - self._last_cards_update >= CONTINUOUS_CARDS_INTERVAL_S:
            # Cartões atualizados poucas vezes por segundo: a cada quadro eles piscariam.
            self._show_report(report)

    def _show_image(self, bgr_image: np.ndarray, mode_text: str, mode_color: str) -> None:
        area_width, area_height = self._video_area_size
        scale = min(area_width / bgr_image.shape[1], area_height / bgr_image.shape[0])
        width, height = round(bgr_image.shape[1] * scale), round(bgr_image.shape[0] * scale)
        resized = cv2.resize(bgr_image, (width, height), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        # PPM em memória: o Tk mostra direto, sem depender do Pillow.
        self._frame_image = tk.PhotoImage(data=f"P6 {width} {height} 255 ".encode() + rgb.tobytes(),
                                          format="PPM")
        self._video.configure(image=self._frame_image)
        self._mode_label.configure(text=mode_text, bg=mode_color)

    # ----- painel de resultado -----

    def _show_report(self, report: InspectionReport) -> None:
        self._last_cards_update = time.monotonic()
        for child in self._cards.winfo_children():
            child.destroy()
        if not report.tomatoes:
            self._show_cards_message("Nenhum tomate inteiro na área amarela.")
        for inspection in report.tomatoes[:MAXIMUM_CARDS]:
            ResultCard(self._cards, inspection).pack(fill="x", pady=(0, 6))
        hidden = len(report.tomatoes) - MAXIMUM_CARDS
        notes: List[str] = [f"+ {hidden} tomate(s): veja a tabela abaixo."] if hidden > 0 else []
        if report.cut_by_border_count:
            notes.append(f"{report.cut_by_border_count} objeto(s) na borda da área: não classificado(s).")
        for note in notes:
            tk.Label(self._cards, text=note, bg=PANEL, fg="#e65100", font=(FONT, 9, "bold"), anchor="w",
                     wraplength=self._scaled(SIDE_PANEL_WIDTH - 30), justify="left").pack(fill="x")

    def _show_cards_message(self, text: str) -> None:
        tk.Label(self._cards, text=text, bg=PANEL, fg=MUTED, font=(FONT, 10), wraplength=self._scaled(SIDE_PANEL_WIDTH - 30),
                 justify="left").pack(anchor="w", pady=10)

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)


def main(arguments: List[str] = None) -> int:
    options = _build_parser().parse_args(arguments)
    _use_sharp_text_on_scaled_windows_screens()
    try:
        setup = _build_setup(options)
        if options.imagem:
            InspectionWindow(StillImageFrameSource(load_image(Path(options.imagem))), setup).run()
            return 0
        camera_address = options.camera or GainFileReader().read_camera_address(Path(options.gain))
        with OpenCvCameraAdapter(parse_camera_address(camera_address)) as camera:
            InspectionWindow(camera, setup).run()
    except (CalibrationError, ValueError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


def _use_sharp_text_on_scaled_windows_screens() -> None:
    # Sem isso, com a escala do Windows em 125%/150% a janela inteira fica borrada (ampliada como imagem).
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)


def _build_setup(options: argparse.Namespace) -> InspectionSetup:
    gain_file = Path(options.gain)
    maturity = maturity_classifier_for(Path(options.lut))
    defect = defect_classifier_for(Path(options.cnn))
    models = InspectionModels(GainFileReader().read_gains(gain_file), ScaleSectionReader().read(gain_file),
                              maturity, defect)
    return InspectionSetup(
        facade=TomatoInspectionFacade(models),
        session=InspectionSession(Path(options.pasta_registro)),
        has_lut=not isinstance(maturity, MissingLutMaturityClassifierNullObject),
        has_cnn=not isinstance(defect, MissingModelDefectClassifierNullObject),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m calibracao_branco.inspection_gui",
                                     description="IHM de classificação de tomates cereja (cor, defeito e tamanho).")
    parser.add_argument("--gain", default="bancada.gain", help="Ganhos do branco, região de interesse e escala.")
    parser.add_argument("--camera", default="", help="Índice ou URL. Sem ela, usa a câmera gravada no .gain.")
    parser.add_argument("--lut", default="lut_cor.npz", help="LUT de cor (gerar_lut.bat).")
    parser.add_argument("--cnn", default="cnn_defeito.onnx", help="CNN de defeitos (treinar_cnn.bat).")
    parser.add_argument("--pasta-registro", default="inspecoes", help="Onde gravar o CSV do dia e as imagens.")
    parser.add_argument("--imagem", default="", help="Usa uma foto no lugar da câmera (teste sem a bancada).")
    return parser


if __name__ == "__main__":
    sys.exit(main())
