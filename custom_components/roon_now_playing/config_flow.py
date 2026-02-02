"""Config flow for Roon Now Playing integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="http://localhost:3000"): str,
    }
)


class RoonNowPlayingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Roon Now Playing."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")

            # Check if already configured
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Test connection
            try:
                await self._test_connection(host)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="Roon Now Playing",
                    data={CONF_HOST: host},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _test_connection(self, host: str) -> None:
        """Test if we can connect to the server."""
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{host}/api/health", timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    raise CannotConnect
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CannotConnect from err


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
