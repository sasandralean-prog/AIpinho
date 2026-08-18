import pytest

from aipinho.services.models.llama_cpp_command_builder import LlamaCppCommandBuilder


def test_llama_cpp_command_builder_builds_argv_and_sanitizes_prompt():
    command = LlamaCppCommandBuilder().build(executable_path="C:/AI/llama-cli.exe", model_path="C:/AI/models/model.gguf", prompt="secret prompt text")
    assert isinstance(command.argv, list)
    assert "--model" in command.argv
    assert "--prompt" in command.argv
    assert "secret prompt text" in command.argv
    assert "secret prompt text" not in command.sanitized
    assert "<prompt chars=" in command.sanitized
    assert "--single-turn" in command.argv
    assert "--reasoning" in command.argv
    assert command.argv[command.argv.index("--reasoning") + 1] == "off"
    assert "--reasoning-budget" in command.argv
    assert command.argv[command.argv.index("--reasoning-budget") + 1] == "0"


def test_llama_cpp_command_builder_blocks_custom_args_by_default():
    with pytest.raises(ValueError, match="custom_args_blocked"):
        LlamaCppCommandBuilder().build(executable_path="x.exe", model_path="m.gguf", prompt="p", custom_args=["--server"])


def test_llama_cpp_command_builder_blocks_shell_policy():
    builder = LlamaCppCommandBuilder(config={"llama_cpp": {"use_shell": True}, "runtime": {}})
    with pytest.raises(ValueError, match="shell_execution_blocked"):
        builder.build(executable_path="x.exe", model_path="m.gguf", prompt="p")
