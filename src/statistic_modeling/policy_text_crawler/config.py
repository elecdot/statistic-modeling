"""Configuration loading for source-specific policy crawlers."""

from __future__ import annotations

import csv
import tomllib
from dataclasses import dataclass
from pathlib import Path


def find_workspace_root(start: Path | None = None) -> Path:
	"""Find the repository root from a script, notebook, or test path."""
	current = (start or Path.cwd()).resolve()
	for candidate in [current, *current.parents]:
		if (candidate / "pyproject.toml").exists():
			return candidate
	raise FileNotFoundError("Could not locate workspace root containing pyproject.toml.")


@dataclass(frozen=True)
class SourceConfig:
	"""Crawler constants and guardrails for one source site."""

	source_id: str
	jurisdiction: str
	source_site: str
	landing_url: str
	gateway: dict
	target_scope: dict
	pagination: dict
	query_parameter_mapping: dict
	request_policy: dict
	artifacts: dict
	status_policy: dict
	notes: dict

	@property
	def gateway_url(self) -> str:
		return str(self.gateway["domain"]).rstrip("/")

	@property
	def list_url(self) -> str:
		return f"{self.gateway_url}{self.gateway['list_endpoint']}"

	@property
	def code_url(self) -> str:
		return f"{self.gateway_url}{self.gateway['code_endpoint']}"


@dataclass(frozen=True)
class QueryBatch:
	"""One reviewed XXGK list-query batch."""

	query_batch_id: str
	source_id: str
	source_site: str
	keyword: str
	search_position: str
	field_name: str
	match_mode: str
	is_precise_search: int
	sort_by: str
	sort_field: str
	page_size: int
	max_pages: int
	enabled: bool
	purpose: str
	review_status: str
	notes: str


def _bool_from_csv(value: str) -> bool:
	return value.strip().lower() in {"1", "true", "yes", "y"}


def load_source_config(path: Path | str) -> SourceConfig:
	"""Read a TOML source config created from the decision notebook."""
	data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
	return SourceConfig(
		source_id=data["source_id"],
		jurisdiction=data["jurisdiction"],
		source_site=data["source_site"],
		landing_url=data["landing_url"],
		gateway=data["gateway"],
		target_scope=data["target_scope"],
		pagination=data["pagination"],
		query_parameter_mapping=data["query_parameter_mapping"],
		request_policy=data["request_policy"],
		artifacts=data["artifacts"],
		status_policy=data["status_policy"],
		notes=data["notes"],
	)


def load_query_batches(path: Path | str, *, enabled_only: bool = True) -> list[QueryBatch]:
	"""Read reviewed query batches from CSV."""
	rows: list[QueryBatch] = []
	with Path(path).open(encoding="utf-8", newline="") as handle:
		for row in csv.DictReader(handle):
			batch = QueryBatch(
				query_batch_id=row["query_batch_id"],
				source_id=row["source_id"],
				source_site=row["source_site"],
				keyword=row["keyword"],
				search_position=row["search_position"],
				field_name=row["field_name"],
				match_mode=row["match_mode"],
				is_precise_search=int(row["is_precise_search"]),
				sort_by=row["sort_by"],
				sort_field=row["sort_field"],
				page_size=int(row["page_size"]),
				max_pages=int(row["max_pages"]),
				enabled=_bool_from_csv(row["enabled"]),
				purpose=row["purpose"],
				review_status=row["review_status"],
				notes=row["notes"],
			)
			if batch.enabled or not enabled_only:
				rows.append(batch)
	return rows
