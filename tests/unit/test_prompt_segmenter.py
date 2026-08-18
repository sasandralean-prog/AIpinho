from aipinho.services.prompt_intelligence.prompt_segmenter import PromptSegmenter


def kinds(prompt: str):
    return {segment.kind for segment in PromptSegmenter().segment(prompt)}


def test_extracts_constraints():
    assert "constraint" in kinds("Explique o projeto sem alterar nada")


def test_extracts_windows_path():
    segments = PromptSegmenter().segment("Explique C:\\Dev\\AIpinho sem alterar nada")

    assert any(segment.kind == "path" and segment.text == "C:\\Dev\\AIpinho" for segment in segments)


def test_extracts_and_normalizes_windows_path_with_forward_separators():
    segments = PromptSegmenter().segment(
        "Explique C:/Workspaces/Projeto sem alterar nada",
    )

    assert any(
        segment.kind == "path" and segment.text == r"C:\Workspaces\Projeto"
        for segment in segments
    )


def test_detects_output_request():
    assert "output_request" in kinds("Salve um relatório em reports/final.md")


def test_casual_prompt_does_not_break():
    segments = PromptSegmenter().segment("Bom dia, tudo certo?")

    assert segments
    assert "question" in {segment.kind for segment in segments}
