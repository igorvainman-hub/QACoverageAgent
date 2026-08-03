import pytest

from src.config import RuntimeConfig, load_runtime_config
from src.main import build_parser


def test_load_runtime_config_returns_values_and_validates_prefix():
    config = load_runtime_config({
        "OPENAI_API_KEY": "sk-test",
        "QA_BASE_PATH": "MyProject",
        "QA_TCID_PREFIX": "QA-123",
    })

    assert config == RuntimeConfig(
        api_key="sk-test",
        base_path="MyProject",
        tcid_prefix="QA-123",
    )


def test_load_runtime_config_requires_required_values():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        load_runtime_config({"QA_BASE_PATH": "MyProject"})

    with pytest.raises(ValueError, match="QA_BASE_PATH"):
        load_runtime_config({"OPENAI_API_KEY": "sk-test"})


def test_load_runtime_config_rejects_invalid_prefix():
    with pytest.raises(ValueError, match="QA_TCID_PREFIX"):
        load_runtime_config({
            "OPENAI_API_KEY": "sk-test",
            "QA_BASE_PATH": "MyProject",
            "QA_TCID_PREFIX": "bad prefix",
        })


def test_build_parser_supports_common_cli_flags():
    parser = build_parser()
    args = parser.parse_args(["generate-docs", "--doc", "auth.md", "--dry-run", "--verbose"])

    assert args.command == "generate-docs"
    assert args.doc == "auth.md"
    assert args.dry_run is True
    assert args.verbose is True
