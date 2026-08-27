class RoutingError(Exception):
    """Base class for routing provider errors."""
    pass

class ConfigurationError(RoutingError):
    """Raised when the provider is not properly configured (e.g., missing API key)."""
    pass

class UnsupportedModeError(RoutingError):
    """Raised when the requested transport mode is not supported by the provider."""
    pass

class NoRouteFoundError(RoutingError):
    """Raised when the provider cannot find a route for the given coordinates."""
    pass

class InvalidCoordinatesError(RoutingError):
    """Raised when invalid coordinates are provided."""
    pass

class ProviderRateLimitError(RoutingError):
    """Raised when the provider rate limit is exceeded."""
    pass

class ProviderTimeoutError(RoutingError):
    """Raised when the provider request times out."""
    pass

class MalformedResponseError(RoutingError):
    """Raised when the provider returns a response that cannot be parsed."""
    pass
