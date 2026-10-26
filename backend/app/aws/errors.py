class AwsError(Exception):
    """Public, credential-free error translated to HTTP by the API."""

    status_code = 503


class AwsConfigurationError(AwsError):
    pass


class AwsPermissionError(AwsError):
    status_code = 403


class AwsConflictError(AwsError):
    status_code = 409


class AwsCaseNotFoundError(AwsError):
    status_code = 404


class AwsProviderError(AwsError):
    status_code = 502
