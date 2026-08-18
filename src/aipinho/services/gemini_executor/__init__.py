__all__ = ["GeminiExecutorService"]


def __getattr__(name: str):
    if name == "GeminiExecutorService":
        from aipinho.services.gemini_executor.gemini_executor_service import GeminiExecutorService

        return GeminiExecutorService
    raise AttributeError(name)
