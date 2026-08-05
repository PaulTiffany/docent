from __future__ import annotations


class ProviderError(RuntimeError):
    public_code = "live_inference_unavailable"
    public_message = "Live inference is temporarily unavailable."

    def __init__(self, message: str = "provider failure", *, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ProviderAuthenticationError(ProviderError):
    public_code = "live_inference_authentication_failed"
    public_message = "Live inference authentication is not configured correctly."


class ProviderAuthorizationError(ProviderError):
    public_code = "live_inference_authorization_failed"
    public_message = "Live inference is not authorized for this request."


class ProviderRateLimitError(ProviderError):
    public_code = "live_inference_rate_limited"
    public_message = "The live inference allowance is temporarily exhausted."


class ProviderTimeoutError(ProviderError):
    public_code = "live_inference_timed_out"
    public_message = "The live inference request timed out."


class ProviderConnectionError(ProviderError):
    pass


class ProviderNoCompatibleModelError(ProviderError):
    public_message = "No compatible live inference model is currently available."


class ProviderModelUnavailableError(ProviderError):
    public_message = "No compatible live inference model is currently available."


class ProviderMalformedResponseError(ProviderError):
    public_code = "live_inference_invalid_response"
    public_message = "The live provider returned an invalid response."


class ModelEnvelopeError(ProviderMalformedResponseError):
    public_message = "The model response did not satisfy Docent's response contract."


class LiveBudgetExhaustedError(ProviderError):
    public_code = "live_inference_budget_exhausted"
    public_message = "The demo's application-level live inference budget is exhausted for today."


class InferenceModeDisabledError(ProviderError):
    public_code = "inference_mode_disabled"
    public_message = "The requested inference mode is disabled on this server."
