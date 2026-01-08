import logging
from typing import Any, Optional

import httpx

import config
from models import InvoiceStatus

logger = logging.getLogger(__name__)


class AiPayClient:
    def __init__(self):
        self.base_url = config.AIPAY_API_URL
        self.headers = {
            "Authorization": f"Bearer {config.AIPAY_BEARER_TOKEN}",
            "Content-Type": "application/json",
        }

    async def create_invoice(
        self, phone: str, amount: int, message: str
    ) -> Optional[dict[str, Any]]:
        """Create a new invoice via AIPay API."""
        url = f"{self.base_url}/api/v1/invoices/createByCompany"
        payload = {
            "account": phone,
            "amount": amount,
            "message": message,
            "companyExternalId": config.AIPAY_COMPANY_EXTERNAL_ID,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Invoice created: {data}")
                return data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating invoice: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return None

    async def get_invoice_status(self, invoice_id: str) -> Optional[dict[str, Any]]:
        """Get invoice status by ID."""
        url = f"{self.base_url}/api/v1/invoices/internal/id/{invoice_id}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting invoice status: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting invoice status: {e}")
            return None

    async def refund_invoice(self, invoice_id: str) -> Optional[dict[str, Any]]:
        """Refund an invoice by ID."""
        url = f"{self.base_url}/api/v1/invoices/refund/{invoice_id}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    url, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"Invoice refunded: {invoice_id}")
                return data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error refunding invoice: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error refunding invoice: {e}")
            return None

    def parse_status(self, response: dict[str, Any]) -> InvoiceStatus:
        """Parse invoice status from API response."""
        # Response format: {'statusDto': {...}, 'obj': {'status': 9, 'statusDescription': '...'}}
        obj = response.get("obj", {})
        status_code = obj.get("status")
        status_desc = obj.get("statusDescription", "").lower()

        # Check by description first (most reliable)
        if "оплачен" in status_desc:
            return InvoiceStatus.PAID
        elif "отменен" in status_desc or "cancel" in status_desc:
            return InvoiceStatus.CANCELLED
        elif "истек" in status_desc or "expir" in status_desc:
            return InvoiceStatus.EXPIRED

        # Fallback to numeric status code
        if status_code == 9:
            return InvoiceStatus.PAID

        return InvoiceStatus.PENDING


# Singleton instance
aipay_client = AiPayClient()
