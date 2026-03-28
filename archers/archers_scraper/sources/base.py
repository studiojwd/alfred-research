from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import ScraperConfig
from ..models import EntitySeed, SourceDocument


LOGGER = logging.getLogger(__name__)


class BaseSourceAdapter(ABC):
    source_name: str
    priority: int
    search_path_template: str

    def __init__(self, config: ScraperConfig) -> None:
        self.config = config
        self._consecutive_failures = 0
        self._disabled_for_run = False
        self.session = requests.Session()
        retry = Retry(
            total=config.retries,
            read=config.retries,
            connect=config.retries,
            status=config.retries,
            allowed_methods=("GET",),
            backoff_factor=config.retry_backoff_seconds,
            status_forcelist=(429, 500, 502, 503, 504),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({"User-Agent": config.user_agent})
        self._last_request_at = 0.0

    def fetch(self, seed: EntitySeed) -> list[SourceDocument]:
        if self._disabled_for_run:
            LOGGER.debug("%s skipped for %s after repeated failures", self.source_name, seed.full_name)
            return []
        search_url = self.build_search_url(seed.full_name)
        try:
            html = self.get(search_url)
            self._consecutive_failures = 0
            return self.parse_search(seed, search_url, html)
        except requests.RequestException as exc:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.config.max_source_failures:
                self._disabled_for_run = True
                LOGGER.warning(
                    "%s disabled for the rest of this run after %s consecutive failures",
                    self.source_name,
                    self._consecutive_failures,
                )
            LOGGER.warning("%s lookup failed for %s: %s", self.source_name, seed.full_name, exc)
            return []

    def build_search_url(self, query: str) -> str:
        return self.search_path_template.format(query=quote_plus(query))

    def get(self, url: str) -> str:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.config.rate_limit_seconds:
            time.sleep(self.config.rate_limit_seconds - elapsed)
        response = self.session.get(url, timeout=self.config.timeout_seconds)
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        return response.text

    def soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def fetch_page(self, url: str) -> str | None:
        try:
            return self.get(url)
        except requests.RequestException as exc:
            LOGGER.debug("%s page fetch failed for %s: %s", self.source_name, url, exc)
            return None

    def absolute_url(self, base_url: str, href: str | None) -> str | None:
        if not href:
            return None
        return requests.compat.urljoin(base_url, href)

    def build_document(
        self,
        seed: EntitySeed,
        source_url: str,
        payload: dict[str, str | list[str]],
        confidence: float,
        notes: list[str] | None = None,
    ) -> SourceDocument:
        return SourceDocument(
            source_name=self.source_name,
            source_url=source_url,
            entity_name=seed.full_name,
            payload=payload,
            confidence=confidence,
            notes=notes or [],
        )

    @abstractmethod
    def parse_search(self, seed: EntitySeed, search_url: str, html: str) -> list[SourceDocument]:
        raise NotImplementedError
