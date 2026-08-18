from aipinho.services.prompt_intelligence.path_extraction_service import PathExtractionService


def test_windows_path_extraction_preserves_bare_paths_with_spaces_on_own_line() -> None:
    service = PathExtractionService()

    paths = service.extract(
        "Projeto\n"
        r"C:\Workspaces\Audio Player Desktop"
        "\nBiblioteca\n"
        r"D:\Media Libraries\pinho music"
        "\nMapear arquivos."
    )

    assert [item.value for item in paths] == [
        r"C:\Workspaces\Audio Player Desktop",
        r"D:\Media Libraries\pinho music",
    ]


def test_windows_path_extraction_stops_before_next_drive() -> None:
    service = PathExtractionService()

    paths = service.extract(r"Compare C:\Project With Spaces D:\Library With Spaces")

    assert [item.value for item in paths] == [
        r"C:\Project With Spaces",
        r"D:\Library With Spaces",
    ]


def test_windows_path_extraction_stops_at_textual_connector_before_second_path() -> None:
    service = PathExtractionService()

    paths = service.extract(r"Analise C:\Dev\AIpinho e o corpus em D:\Media Library")

    assert [item.value for item in paths] == [
        r"C:\Dev\AIpinho",
        r"D:\Media Library",
    ]
