from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dera.permissions.pairing import PairingService
from dera.relay.protocol import signed_envelope
from dera.relay.store import RelayStore


class OutboundRelayClient:
    """Posts signed runtime events outward; it never opens an inbound listener."""

    def status(self) -> dict:
        return RelayStore().get()

    def heartbeat(self, retry_on_auth_failure: bool = True) -> dict:
        store = RelayStore()
        config = store.get()
        if not config["enabled"] or not config["relay_url"]:
            return {"sent": False, "message": "Outbound relay is not configured or enabled."}
        if not config["relay_url"].startswith("https://"):
            return {"sent": False, "message": "A production relay URL must use HTTPS."}
        device_id = PairingService().status()["device_id"] or PairingService().create_code()["device_id"]
        token = store.token()
        if not token:
            registration = Request(
                config["relay_url"].rstrip("/") + "/v1/devices/register",
                data=json.dumps({"device_id": device_id}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(registration, timeout=10) as response:
                    token = json.loads(response.read())["device_token"]
            except (URLError, KeyError, json.JSONDecodeError) as error:
                return {"sent": False, "message": f"Device enrollment with the relay failed: {error}"}
            store.save_token(token)
        envelope = signed_envelope(device_id, "runtime.heartbeat", {"runtime": "moon", "scope": "local-only"}, store.secret())
        request = Request(
            config["relay_url"].rstrip("/") + f"/v1/devices/{device_id}/events",
            data=json.dumps(envelope).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                response.read()
        except HTTPError as error:
            if error.code == 401 and retry_on_auth_failure:
                store.clear_token()
                return self.heartbeat(retry_on_auth_failure=False)
            return {"sent": False, "message": f"The outbound relay rejected this device: HTTP {error.code}."}
        except URLError as error:
            return {"sent": False, "message": f"The outbound relay could not be reached: {error.reason}"}
        self.publish_pairing_codes()
        return {"sent": True, "message": "Signed heartbeat sent through the outbound relay."}

    def publish_snapshot(self, snapshot: dict) -> dict:
        """Publish only the current read-only system snapshot to the configured relay."""
        store, config = RelayStore(), RelayStore().get()
        device_id = PairingService().status()["device_id"]
        if not config["enabled"] or not config["relay_url"] or not store.token() or not device_id:
            return {"sent": False, "message": "Outbound relay is not configured or enrolled."}
        envelope = signed_envelope(device_id, "runtime.snapshot", {"snapshot": snapshot}, store.secret())
        request = Request(
            config["relay_url"].rstrip("/") + f"/v1/devices/{device_id}/events",
            data=json.dumps(envelope).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {store.token()}"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                response.read()
            return {"sent": True}
        except HTTPError as error:
            return {"sent": False, "message": f"The relay rejected the system snapshot: HTTP {error.code}."}
        except URLError as error:
            return {"sent": False, "message": f"The relay could not receive the system snapshot: {error.reason}"}

    def publish_pairing_codes(self) -> dict:
        """Publish only active code hashes; browser sessions never reach the PC."""
        store, config = RelayStore(), RelayStore().get()
        device_id = PairingService().status()["device_id"]
        if not config["enabled"] or not config["relay_url"] or not store.token() or not device_id:
            return {"published": False}
        body = {"codes": PairingService().active_code_records()}
        request = Request(
            config["relay_url"].rstrip("/") + f"/v1/devices/{device_id}/pairing-codes",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {store.token()}"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                return {"published": True, **json.loads(response.read())}
        except (URLError, json.JSONDecodeError):
            return {"published": False}

    def poll_commands(self) -> dict:
        store, config = RelayStore(), RelayStore().get()
        if not config["enabled"] or not config["relay_url"]:
            return {"commands": [], "message": "Outbound relay is not configured or enabled."}
        if not store.token():
            enrollment = self.heartbeat()
            if not enrollment["sent"]:
                return {"commands": [], "message": enrollment["message"]}
        device_id = PairingService().status()["device_id"]
        request = Request(config["relay_url"].rstrip("/") + f"/v1/devices/{device_id}/commands", headers={"Authorization": f"Bearer {store.token()}"})
        try:
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read())
        except HTTPError as error:
            if error.code == 401:
                store.clear_token()
            return {"commands": [], "message": f"Relay command poll failed: HTTP {error.code}."}
        except (URLError, json.JSONDecodeError) as error:
            return {"commands": [], "message": f"Relay command poll failed: {error}"}
    def send_result(self, command_id: str, result: dict) -> dict:
        store, config = RelayStore(), RelayStore().get()
        device_id = PairingService().status()["device_id"]
        if not config["enabled"] or not store.token() or not device_id:
            return {"sent": False}
        envelope = signed_envelope(device_id, "command.result", {"command_id": command_id, "result": result}, store.secret())
        request = Request(config["relay_url"].rstrip("/") + f"/v1/devices/{device_id}/events", data=json.dumps(envelope).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {store.token()}"}, method="POST")
        try:
            with urlopen(request, timeout=10) as response:
                response.read()
            return {"sent": True}
        except URLError:
            return {"sent": False}

    def browser_sessions(self) -> dict:
        store, config = RelayStore(), RelayStore().get()
        device_id = PairingService().status()["device_id"]
        if not config["enabled"] or not config["relay_url"] or not store.token() or not device_id:
            return {"clients": [], "message": "Outbound relay is not configured or enabled."}
        request = Request(config["relay_url"].rstrip("/") + f"/v1/devices/{device_id}/browser-sessions", headers={"Authorization": f"Bearer {store.token()}"})
        try:
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read())
        except (URLError, json.JSONDecodeError) as error:
            return {"clients": [], "message": f"Paired browser list could not be loaded: {error}"}

    def revoke_browser_session(self, client_id: str) -> dict:
        store, config = RelayStore(), RelayStore().get()
        device_id = PairingService().status()["device_id"]
        if not config["enabled"] or not config["relay_url"] or not store.token() or not device_id:
            return {"revoked": False, "message": "Outbound relay is not configured or enabled."}
        request = Request(config["relay_url"].rstrip("/") + f"/v1/devices/{device_id}/browser-sessions/{client_id}", headers={"Authorization": f"Bearer {store.token()}"}, method="DELETE")
        try:
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read())
        except (URLError, json.JSONDecodeError) as error:
            return {"revoked": False, "message": f"Paired browser could not be revoked: {error}"}
