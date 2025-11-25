"""
API client for interacting with n8n's REST API.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


class N8nAPIClient:
    """
    Lightweight client for n8n REST API.

    Supports listing workflows so we can show them in the Django admin
    without granting admins direct access to n8n credentials.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 15,
    ) -> None:
        self.base_url = (base_url or settings.N8N_API_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.N8N_API_KEY
        self.timeout = timeout

        if not self.api_key:
            logger.warning("N8n API key is not configured. Workflow sync will be disabled.")

    @cached_property
    def session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "GRA-n8n-admin/1.0",
            }
        )
        if self.api_key:
            session.headers["X-N8N-API-KEY"] = self.api_key
        return session

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Internal helper to perform an HTTP request."""
        if not self.api_key:
            raise RuntimeError("N8n API key is not configured.")

        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            if not response.content:
                return {}
            return response.json()
        except requests.HTTPError as exc:
            logger.error("n8n API error %s %s: %s", method, url, exc, exc_info=True)
            raise

    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        Return all workflows available in n8n.

        Response structure may differ between versions; we normalize to a list.
        """
        data = self._request("GET", "/rest/workflows")
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        if isinstance(data, list):
            return data
        logger.warning("Unexpected n8n workflow response format: %s", type(data))
        return []

    def get_workflow(self, workflow_id: int) -> Dict[str, Any]:
        """Fetch a single workflow by ID."""
        return self._request("GET", f"/rest/workflows/{workflow_id}")


