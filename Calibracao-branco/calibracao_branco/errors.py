class CalibrationError(Exception):
    """Falha que impede calibrar ou medir com confiança."""


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


class NoObjectFoundError(CalibrationError):
    pass


class ObjectTouchesRegionBorderError(CalibrationError):
    pass
