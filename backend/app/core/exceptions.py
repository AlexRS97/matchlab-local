class ProviderError(RuntimeError):
    """Sanitized error safe to show in the provider status panel."""


class QuotaExceeded(ProviderError):
    pass


class CircuitOpen(ProviderError):
    pass
