"""Gateway request helpers for the public gov.cn XXGK search page."""

from __future__ import annotations

import base64
import json
import secrets
from urllib.parse import quote
from urllib.request import Request, urlopen

from statistic_modeling.policy_text_crawler.config import QueryBatch, SourceConfig


def _read_der_length(data: bytes, offset: int) -> tuple[int, int]:
	first = data[offset]
	offset += 1
	if first < 0x80:
		return first, offset
	length_size = first & 0x7F
	length = int.from_bytes(data[offset : offset + length_size], "big")
	return length, offset + length_size


def _read_der_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
	tag = data[offset]
	length, value_start = _read_der_length(data, offset + 1)
	value_end = value_start + length
	return tag, data[value_start:value_end], value_end


def parse_spki_rsa_public_key(public_key_base64: str) -> tuple[int, int]:
	"""Extract RSA modulus and exponent from a SubjectPublicKeyInfo DER blob."""
	der = base64.b64decode(public_key_base64)
	tag, spki, _ = _read_der_tlv(der, 0)
	if tag != 0x30:
		raise ValueError("Expected SubjectPublicKeyInfo sequence.")

	offset = 0
	_, _, offset = _read_der_tlv(spki, offset)
	bit_string_tag, bit_string, _ = _read_der_tlv(spki, offset)
	if bit_string_tag != 0x03 or not bit_string:
		raise ValueError("Expected RSA public key bit string.")

	rsa_key_der = bit_string[1:]
	rsa_tag, rsa_sequence, _ = _read_der_tlv(rsa_key_der, 0)
	if rsa_tag != 0x30:
		raise ValueError("Expected RSA public key sequence.")

	offset = 0
	modulus_tag, modulus_bytes, offset = _read_der_tlv(rsa_sequence, offset)
	exponent_tag, exponent_bytes, _ = _read_der_tlv(rsa_sequence, offset)
	if modulus_tag != 0x02 or exponent_tag != 0x02:
		raise ValueError("Expected RSA integer fields.")
	return int.from_bytes(modulus_bytes, "big"), int.from_bytes(exponent_bytes, "big")


def rsa_encrypt_pkcs1_v15(message: str, public_key_base64: str) -> str:
	"""Match the browser-side JSEncrypt output shape for the gateway header."""
	modulus, exponent = parse_spki_rsa_public_key(public_key_base64)
	key_size = (modulus.bit_length() + 7) // 8
	message_bytes = message.encode("utf-8")
	padding_size = key_size - len(message_bytes) - 3
	if padding_size < 8:
		raise ValueError("Message is too long for this RSA key.")

	padding = bytearray()
	while len(padding) < padding_size:
		candidate = secrets.token_bytes(padding_size - len(padding))
		padding.extend(byte for byte in candidate if byte != 0)
	encoded = b"\x00\x02" + bytes(padding[:padding_size]) + b"\x00" + message_bytes
	encrypted_int = pow(int.from_bytes(encoded, "big"), exponent, modulus)
	return base64.b64encode(encrypted_int.to_bytes(key_size, "big")).decode("ascii")


def ajax_headers(config: SourceConfig) -> dict[str, str]:
	"""Build browser-like headers for the public XXGK AJAX gateway.

	This uses page-observed constants, not private credentials. Keep usage bounded
	and explicitly enabled by the caller.
	"""
	gateway = config.gateway
	encrypted_key = rsa_encrypt_pkcs1_v15(gateway["page_observed_app_key"], gateway["page_observed_public_key"])
	return {
		"User-Agent": config.request_policy["user_agent"],
		"Referer": config.request_policy["referer"],
		"Content-Type": "application/json;charset=utf-8",
		"athenaAppKey": quote(encrypted_key, safe=""),
		"athenaAppName": quote(gateway["athena_app_name"], safe=""),
	}


def request_json(config: SourceConfig, url: str, payload: dict | None = None) -> dict:
	"""Send one bounded JSON GET/POST request through urllib."""
	data = None
	method = "GET"
	if payload is not None:
		data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
		method = "POST"
	request = Request(url, data=data, headers=ajax_headers(config), method=method)
	with urlopen(request, timeout=int(config.request_policy["timeout_seconds"])) as response:
		text = response.read().decode("utf-8", errors="replace")
	parsed = json.loads(text)
	return json.loads(parsed) if isinstance(parsed, str) else parsed


def build_code_url(config: SourceConfig) -> str:
	return f"{config.code_url}?thirdPartyName=hycloud&thirdPartyTenantId={config.gateway['site_id']}"


def build_list_payload(config: SourceConfig, batch: QueryBatch, *, code: str, page_no: int) -> dict:
	"""Create the list-query payload for one reviewed batch and page."""
	return {
		"code": code,
		"thirdPartyCode": config.gateway["third_party_code"],
		"thirdPartyTableId": config.gateway["view_id"],
		"resultFields": ["pub_url", "maintitle", "fwzh", "cwrq", "publish_time"],
		"trackTotalHits": "true",
		"searchFields": [{"fieldName": batch.field_name, "searchWord": batch.keyword}],
		"isPreciseSearch": batch.is_precise_search,
		"sorts": [{"sortField": batch.sort_field, "sortOrder": "DESC"}],
		"childrenInfoIds": [],
		"pageSize": batch.page_size,
		"pageNo": page_no,
	}
