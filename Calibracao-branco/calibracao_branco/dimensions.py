from typing import Tuple


def parse_columns_by_rows(text: str) -> Tuple[int, int]:
    """Lê 'colunas x linhas' (ex.: '9x6') e devolve (colunas, linhas)."""
    parts = text.lower().replace(" ", "").split("x")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Use o formato colunas x linhas (ex.: 9x6), recebido: '{text}'.")
    return int(parts[0]), int(parts[1])


def format_columns_by_rows(columns: int, rows: int) -> str:
    return f"{columns}x{rows}"
