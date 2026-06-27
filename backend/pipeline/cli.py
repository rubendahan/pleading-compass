"""Command-line entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import load_config, load_env_file
from .embeddings import build_embedding_client
from .graph_store import check_neo4j_connection
from .model_providers import build_llm_client
from .pipeline import run_phase0
from .phase1 import run_phase1
from .phase2 import run_phase2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    phase0 = subparsers.add_parser("phase0", help="Initialize the phase 0 case graph.")
    phase0.add_argument("--case", required=True, help="Path to a case directory.")
    phase0.add_argument("--config", default="configs/default.yaml", help="Path to config YAML.")
    phase0.add_argument("--env-file", default=".env", help="Path to a local .env file.")
    phase0.add_argument("--out", required=True, help="Output run directory.")
    phase0.add_argument("--prompts", default="prompts", help="Prompt directory.")

    phase1 = subparsers.add_parser("phase1", help="Compute phase 1 graph edges.")
    phase1.add_argument("--phase0", required=True, help="Path to a completed phase 0 output directory.")
    phase1.add_argument("--config", default="configs/default.yaml", help="Path to config YAML.")
    phase1.add_argument("--env-file", default=".env", help="Path to a local .env file.")
    phase1.add_argument("--out", required=True, help="Output run directory.")
    phase1.add_argument("--prompts", default="prompts", help="Prompt directory.")

    phase2 = subparsers.add_parser("phase2", help="Review claim robustness from phase 1 graph outputs.")
    phase2.add_argument("--phase1", required=True, help="Path to a completed phase 1 output directory.")
    phase2.add_argument("--config", default="configs/default.yaml", help="Path to config YAML.")
    phase2.add_argument("--env-file", default=".env", help="Path to a local .env file.")
    phase2.add_argument("--out", required=True, help="Output run directory.")
    phase2.add_argument("--prompts", default="prompts", help="Prompt directory.")

    check_openai = subparsers.add_parser(
        "check-openai",
        help="Check the configured OpenAI or Azure OpenAI LLM and embedding runtime.",
    )
    check_openai.add_argument("--config", default="configs/default.yaml", help="Path to config YAML.")
    check_openai.add_argument("--env-file", default=".env", help="Path to a local .env file.")
    check_openai.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip the small LLM health-check call.",
    )
    check_openai.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip the small embedding health-check call.",
    )

    check_runtime = subparsers.add_parser(
        "check-runtime",
        help="Check the configured LLM and embedding runtime.",
    )
    check_runtime.add_argument("--config", default="configs/default.yaml", help="Path to config YAML.")
    check_runtime.add_argument("--env-file", default=".env", help="Path to a local .env file.")
    check_runtime.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip the small LLM health-check call.",
    )
    check_runtime.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip the small embedding health-check call.",
    )

    check_neo4j = subparsers.add_parser(
        "check-neo4j",
        help="Check the configured Neo4j connection.",
    )
    check_neo4j.add_argument("--config", default="configs/default.yaml", help="Path to config YAML.")
    check_neo4j.add_argument("--env-file", default=".env", help="Path to a local .env file.")

    args = parser.parse_args(argv)
    if args.command == "phase0":
        return _run_phase0(args)
    if args.command == "phase1":
        return _run_phase1(args)
    if args.command == "phase2":
        return _run_phase2(args)
    if args.command in {"check-openai", "check-runtime"}:
        return _check_runtime(args)
    if args.command == "check-neo4j":
        return _check_neo4j(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_phase0(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    try:
        load_env_file(Path(args.env_file))
        config = load_config(config_path)
        metadata = run_phase0(
            case_dir=Path(args.case),
            config=config,
            config_path=config_path,
            output_dir=Path(args.out),
            prompts_dir=Path(args.prompts),
        )
    except Exception as exc:
        print(f"phase0 failed: {exc}", file=sys.stderr)
        return 1

    print(f"Phase 0 complete for case {metadata.case_id}.")
    print(f"Output directory: {Path(args.out)}")
    if metadata.warnings:
        print("Warnings:")
        for warning in metadata.warnings:
            print(f"- {warning}")
    return 0


def _run_phase1(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    try:
        load_env_file(Path(args.env_file))
        config = load_config(config_path)
        metadata = run_phase1(
            phase0_dir=Path(args.phase0),
            config=config,
            config_path=config_path,
            output_dir=Path(args.out),
            prompts_dir=Path(args.prompts),
        )
    except Exception as exc:
        print(f"phase1 failed: {exc}", file=sys.stderr)
        return 1

    print(f"Phase 1 complete for case {metadata.case_id}.")
    print(f"Output directory: {Path(args.out)}")
    print(
        "Edges: "
        f"claim/evidence SIMILAR_TO={metadata.claim_evidence_similarity_edges}, "
        f"evidence/evidence SIMILAR_TO={metadata.evidence_evidence_similarity_edges}, "
        f"SUPPORTS={metadata.support_edges}, "
        f"CONTRADICTS={metadata.contradict_edges}"
    )
    if metadata.warnings:
        print("Warnings:")
        for warning in metadata.warnings:
            print(f"- {warning}")
    return 0


def _run_phase2(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    try:
        load_env_file(Path(args.env_file))
        config = load_config(config_path)
        metadata = run_phase2(
            phase1_dir=Path(args.phase1),
            config=config,
            config_path=config_path,
            output_dir=Path(args.out),
            prompts_dir=Path(args.prompts),
        )
    except Exception as exc:
        print(f"phase2 failed: {exc}", file=sys.stderr)
        return 1

    print(f"Phase 2 complete for case {metadata.case_id}.")
    print(f"Output directory: {Path(args.out)}")
    print(
        "Claim reports: "
        f"{metadata.claim_reports}, top_k={metadata.claim_evidence_top_k}"
    )
    if metadata.warnings:
        print("Warnings:")
        for warning in metadata.warnings:
            print(f"- {warning}")
    return 0


def _check_runtime(args: argparse.Namespace) -> int:
    try:
        load_env_file(Path(args.env_file))
        config = load_config(Path(args.config))

        if args.skip_llm and args.skip_embeddings:
            raise RuntimeError("Nothing to check: both --skip-llm and --skip-embeddings were set.")

        if not args.skip_llm:
            llm_client = build_llm_client(config.llm)
            response_id = llm_client.check_connection()
            print(
                "LLM check ok: "
                f"provider={llm_client.provider_name}, model={llm_client.model_id}, "
                f"response_id={response_id}"
            )

        if not args.skip_embeddings:
            embedding_client = build_embedding_client(config.embeddings)
            embedding = embedding_client.embed_text("Pipeline embedding health check.")
            print(
                "Embedding check ok: "
                f"provider={embedding_client.provider_name}, "
                f"model={embedding_client.model_id}, dimensions={len(embedding)}"
            )
    except Exception as exc:
        print(f"Runtime check failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _check_neo4j(args: argparse.Namespace) -> int:
    try:
        load_env_file(Path(args.env_file))
        config = load_config(Path(args.config))
        check_neo4j_connection(config.neo4j)
    except Exception as exc:
        print(f"Neo4j check failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Neo4j check ok: "
        f"uri_env={config.neo4j.uri_env}, user_env={config.neo4j.user_env}, "
        f"database={config.neo4j.database}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
