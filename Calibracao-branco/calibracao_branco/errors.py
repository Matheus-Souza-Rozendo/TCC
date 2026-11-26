class CalibrationError(Exception):
    """Falha que impede gerar um arquivo de calibração confiável."""


class CameraUnavailableError(CalibrationError):
    pass


class WhiteReferenceSaturatedError(CalibrationError):
    pass


class WhiteReferenceTooDarkError(CalibrationError):
    pass


class CalibrationCancelledError(CalibrationError):
    pass


class CalibrationFileFormatError(CalibrationError):
    pass


class ChessboardNotFoundError(CalibrationError):
    pass


class IncompleteRegionCoverageError(CalibrationError):
    pass
