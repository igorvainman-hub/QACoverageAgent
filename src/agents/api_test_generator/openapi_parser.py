from __future__ import annotations

import json
import ipaddress
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

JSON_ONLY_MESSAGE = (
    "Only JSON OpenAPI specs are supported. Convert YAML to JSON first "
    "(e.g. via 'yq -o=json spec.yaml > spec.json' or an online converter) "
    "and pass the .json file via --openapi."
)
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


class OpenAPIParseError(ValueError):
    """A user-facing error while loading or validating an OpenAPI JSON document."""


class _NoRedirect(HTTPRedirectHandler):
    """Prevent a public URL from redirecting a CLI request to a private address."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass(frozen=True)
class OpenAPIEndpoint:
    method: str
    path: str
    operation_id: str | None
    summary: str
    request_schema: dict[str, Any] | None
    response_schema: dict[str, Any] | None
    tag: str


def load_openapi_json(source: str) -> dict[str, Any]:
    """Load a local file or HTTP(S) URL and return a JSON object."""
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        _validate_remote_url(parsed)
    try:
        if parsed.scheme in {"http", "https"}:
            request = Request(source, headers={"Accept": "application/json"})
            with build_opener(_NoRedirect).open(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
        else:
            if parsed.scheme and len(parsed.scheme) != 1:
                raise OpenAPIParseError("Only local files and HTTP(S) OpenAPI URLs are supported.")
            raw = Path(source).read_text(encoding="utf-8-sig")
        value = json.loads(raw)
    except OpenAPIParseError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OpenAPIParseError(JSON_ONLY_MESSAGE) from error
    if not isinstance(value, dict):
        raise OpenAPIParseError("OpenAPI JSON root must be an object.")
    return value


def _validate_remote_url(parsed) -> None:  # type: ignore[no-untyped-def]
    if not parsed.hostname or parsed.username or parsed.password:
        raise OpenAPIParseError("OpenAPI URL must contain a hostname and must not contain credentials.")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise OpenAPIParseError(f"Unable to resolve OpenAPI URL host: {parsed.hostname}") from error
    if not addresses:
        raise OpenAPIParseError(f"Unable to resolve OpenAPI URL host: {parsed.hostname}")
    if any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise OpenAPIParseError("OpenAPI URL must not resolve to a private, loopback, link-local, or reserved address.")


def parse_openapi(spec: dict[str, Any]) -> dict[tuple[str, str], OpenAPIEndpoint]:
    """Extract supported HTTP operations from a validated OpenAPI JSON object."""
    if not isinstance(spec.get("info"), dict) or not isinstance(spec.get("paths"), dict):
        raise OpenAPIParseError("Invalid OpenAPI spec: top-level 'info' and 'paths' objects are required.")

    endpoints: dict[tuple[str, str], OpenAPIEndpoint] = {}
    for path, path_item in spec["paths"].items():
        if not isinstance(path, str) or not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            normalized_method = method.upper()
            tags = operation.get("tags")
            tag = tags[0] if isinstance(tags, list) and tags and isinstance(tags[0], str) else "default"
            endpoints[(normalized_method, path)] = OpenAPIEndpoint(
                method=normalized_method,
                path=path,
                operation_id=_string_or_none(operation.get("operationId")),
                summary=_string_or_empty(operation.get("summary")),
                request_schema=_request_schema(operation),
                response_schema=_response_schema(operation),
                tag=tag,
            )
    if not endpoints:
        raise OpenAPIParseError("Invalid OpenAPI spec: 'paths' contains no HTTP operations.")
    return endpoints


def _request_schema(operation: dict[str, Any]) -> dict[str, Any] | None:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return None
    return _content_schema(request_body.get("content"))


def _response_schema(operation: dict[str, Any]) -> dict[str, Any] | None:
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return None
    for status, response in responses.items():
        if str(status).startswith("2") and isinstance(response, dict):
            return _content_schema(response.get("content"))
    return None


def _content_schema(content: Any) -> dict[str, Any] | None:
    if not isinstance(content, dict):
        return None
    for media_type in ("application/json", *content):
        media = content.get(media_type)
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            return media["schema"]
    return None


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _string_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""
