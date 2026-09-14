import ssl
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import Settings
from app.core.exceptions import ProviderError


class BetfairSession:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.token: str | None = None
        self.expires = datetime.min.replace(tzinfo=UTC)
        context = ssl.create_default_context()
        self.certificate_error = False
        if settings.betfair_cert_path:
            try:
                context.load_cert_chain(
                    settings.betfair_cert_path, settings.betfair_key_path or None
                )
            except (OSError, ssl.SSLError):
                self.certificate_error = True
        self.client = client or httpx.AsyncClient(timeout=30, verify=context)

    async def headers(self) -> dict:
        if self.certificate_error:
            raise ProviderError("Betfair: no se pudo cargar el certificado configurado")
        if self.token and self.expires > datetime.now(UTC):
            return {
                "X-Application": self.settings.betfair_app_key.get_secret_value(),
                "X-Authentication": self.token,
            }
        domain = self.settings.betfair_identity_domain
        if domain not in {"betfair.com", "betfair.es", "betfair.it", "betfair.com.au"}:
            raise ProviderError("Betfair: dominio de identidad no válido")
        headers = {
            "Accept": "application/json",
            "X-Application": self.settings.betfair_app_key.get_secret_value(),
        }
        try:
            if self.token:
                response = await self.client.post(
                    f"https://identitysso.{domain}/api/keepAlive",
                    headers={**headers, "X-Authentication": self.token},
                )
                data = response.json()
                if response.is_success and data.get("status") == "SUCCESS":
                    self.expires = datetime.now(UTC) + timedelta(minutes=15)
                    return {**headers, "X-Authentication": self.token}
            cert = bool(self.settings.betfair_cert_path)
            identity = f"identitysso-cert.{domain}" if cert else f"identitysso.{domain}"
            response = await self.client.post(
                f"https://{identity}/api/{'certlogin' if cert else 'login'}",
                headers=headers,
                data={
                    "username": self.settings.betfair_username.get_secret_value(),
                    "password": self.settings.betfair_password.get_secret_value(),
                },
            )
            data = response.json()
            if not response.is_success or data.get("loginStatus", data.get("status")) != "SUCCESS":
                raise ProviderError(
                    "Betfair: inicio de sesión rechazado; revisa credenciales, certificado, 2FA o condiciones de cuenta"
                )
            self.token = data.get("sessionToken", data.get("token"))
            if not self.token:
                raise ProviderError("Betfair: respuesta de login sin sesión")
            self.expires = datetime.now(UTC) + timedelta(minutes=15)
            return {**headers, "X-Authentication": self.token}
        except (httpx.HTTPError, ValueError):
            raise ProviderError("Betfair: no se pudo iniciar o renovar la sesión") from None

    def invalidate(self):
        self.token = None
        self.expires = datetime.min.replace(tzinfo=UTC)

    async def close(self):
        await self.client.aclose()
