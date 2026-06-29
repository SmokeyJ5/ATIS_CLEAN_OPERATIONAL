from __future__ import annotations


class ProviderAdapter:
    name = "Base Provider"

    def status(self) -> dict:
        return {"name": self.name, "status": "STUB"}

    def fetch_quote(self, symbol: str) -> dict:
        raise NotImplementedError("Provider adapter has not implemented fetch_quote.")


class NewsProviderStub(ProviderAdapter):
    name = "News Provider Stub"

    def fetch_news(self, symbol: str) -> list[dict]:
        return []


class EconomicCalendarProviderStub(ProviderAdapter):
    name = "Economic Calendar Provider Stub"

    def fetch_events(self) -> list[dict]:
        return []


news_provider_stub = NewsProviderStub()
economic_calendar_stub = EconomicCalendarProviderStub()
