class CalibrationError(Exception):
    """Falha que impede gerar um arquivo de ganho confiável."""


class CameraUnavailableError(CalibrationError):
    pass


class WhiteReferenceSaturatedError(CalibrationError):
    pass


class WhiteReferenceTooDarkError(CalibrationError):
    pass


class CalibrationCancelledError(CalibrationError):
    pass


class GainFileFormatError(CalibrationError):
    pass
