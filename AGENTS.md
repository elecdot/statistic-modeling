# AGENTS.md

Read `README.md` and relevant directory-level `README.md` files first for the
project overview and local conventions.

## Project Goal

The Causal Effect of the "Specialized, Refined, Distinctive, and Innovative"
(SRDI) Policy on Enterprise Innovation: A Dual-Layer Analysis Based on Staggered DID
and Policy Text Mining.

## Core Research Questions

- **Main question:** Does recognition as a "Specialized, Refined,
  Distinctive, and Innovative Little Giant" significantly promote enterprise
  innovation output, such as patent counts and R&D investment?
- **Policy-intensity question:** Do provincial differences in supporting policy
  instruments affect the policy effect? Which policy tools are more effective:
  supply-side, demand-side, or environmental tools?
- **Heterogeneity question:** Do enterprises in different regions, economic
  development levels, or technology-agglomeration environments experience
  heterogeneous policy effects?

## Agent Role

Use domain knowledge from data science, statistics, computer science, and policy
research. Keep changes aligned with the causal-inference and policy-text-mining
purpose of the project.

## Working Notes

- Since `uv` is blocked by a read-only cache path in the agent's sandbox,
use a workspace-safe cache directory instead, e.g., `UV_CACHE_DIR=/tmp/uv-cache uv <command>`.
- Do not be constrained by the repository's current dependency set. When a task
reasonably needs a missing dependency, add it autonomously using the project's
dependency-management conventions (basically `uv add`).
- If you identify commands during development that should be documented or
reused, consider adding them to `justfile` with appropriate guidance (for
example, comments).
- Keep documentation complete and in sync throughout development; if you find
gaps, fill them in.
- Always add appropriate comments when working.
