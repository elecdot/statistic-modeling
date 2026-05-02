from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_source_manifest_globs_do_not_mix_srdi_and_all_policy_cache() -> None:
	manifest = pd.read_csv(ROOT / "data" / "source-manifest.csv").fillna("")
	assert len(manifest) == 33
	assert {
		"generated_by",
		"config_files",
		"upstream_files",
		"quality_report",
		"collection_status",
		"review_status",
		"record_count",
	}.issubset(manifest.columns)

	def resolve_grouped_globs(value: str) -> list[Path]:
		matches: list[Path] = []
		for pattern in value.split(";"):
			pattern = pattern.strip()
			if pattern:
				matches.extend((ROOT / "data").glob(pattern))
		return sorted(matches)

	srdi_json_row = manifest.loc[manifest["source_name"] == "政府信息公开平台_中国政府网_Crawler列表JSON"].iloc[0]
	all_json_row = manifest.loc[manifest["source_name"] == "政府信息公开平台_中国政府网_AllPolicy列表JSON"].iloc[0]

	srdi_matches = resolve_grouped_globs(srdi_json_row["local_file"])
	all_matches = resolve_grouped_globs(all_json_row["local_file"])

	assert srdi_matches
	assert len(all_matches) == 76
	assert all("govcn_xxgk_all" not in path.name for path in srdi_matches)
	assert all("govcn_xxgk_all" in path.name for path in all_matches)
