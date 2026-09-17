from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

from aipinho.schemas.runtime.remote_repository_scope import RemoteRepositoryIdentity


class RemoteRepositoryIdentityService:
    """Normalizes remote repository locators without retaining credentials."""

    _SCP = re.compile(
        r"^(?P<user>[^@\s]+)@(?P<host>[A-Za-z0-9.-]+):(?P<path>[^\s]+)$"
    )
    _KNOWN_PROVIDERS = {
        "github.com": "github",
        "gitlab.com": "gitlab",
        "bitbucket.org": "bitbucket",
    }

    def normalize(self, locator: str) -> RemoteRepositoryIdentity:
        raw = self._clean(locator)
        if not raw:
            raise ValueError("remote_repository_locator_missing")
        scp = self._SCP.match(raw)
        if scp:
            return self._identity(
                scheme="ssh",
                host=scp.group("host"),
                path=scp.group("path"),
                secret_material_detected=False,
            )
        parsed = urlsplit(raw)
        if parsed.scheme and parsed.hostname:
            secret = bool(parsed.password) or (
                bool(parsed.username) and parsed.username.casefold() not in {"git"}
            )
            return self._identity(
                scheme=parsed.scheme.casefold(),
                host=parsed.hostname,
                path=parsed.path,
                secret_material_detected=secret,
            )
        if re.match(r"^[A-Za-z0-9.-]+/[A-Za-z0-9_.\-/]+$", raw):
            host, path = raw.split("/", 1)
            if "." in host:
                return self._identity(
                    scheme="https",
                    host=host,
                    path=path,
                    secret_material_detected=False,
                )
        raise ValueError("remote_repository_locator_invalid")

    def equivalent(self, left: str, right: str) -> bool:
        try:
            return self.normalize(left).normalized_identity == self.normalize(right).normalized_identity
        except ValueError:
            return False
    def _identity(
        self,
        *,
        scheme: str,
        host: str,
        path: str,
        secret_material_detected: bool,
    ) -> RemoteRepositoryIdentity:
        normalized_host = str(host).strip().casefold().rstrip(".")
        repository_path = unquote(str(path)).replace("\\", "/").strip("/")
        if repository_path.casefold().endswith(".git"):
            repository_path = repository_path[:-4]
        repository_path = re.sub(r"/+", "/", repository_path).strip("/")
        if not normalized_host or not repository_path or repository_path in {".", ".."}:
            raise ValueError("remote_repository_identity_invalid")
        provider = self._KNOWN_PROVIDERS.get(normalized_host, normalized_host)
        identity_path = (
            repository_path.casefold()
            if normalized_host in self._KNOWN_PROVIDERS
            else repository_path
        )
        normalized_identity = f"{normalized_host}/{identity_path}"
        normalized_locator = f"https://{normalized_host}/{repository_path}.git"
        return RemoteRepositoryIdentity(
            provider=provider,
            host=normalized_host,
            repository_path=repository_path,
            normalized_identity=normalized_identity,
            normalized_locator=normalized_locator,
            scheme=scheme,
            secret_material_detected=secret_material_detected,
        )

    def _clean(self, locator: str) -> str:
        return str(locator or "").strip().strip("`\"'<>[](){}.,; ")
