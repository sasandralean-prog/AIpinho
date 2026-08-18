from aipinho.services.patching.patch_hunk_builder import PatchHunkBuilder


def test_patch_hunk_builder_needs_original_and_replacement():
    builder = PatchHunkBuilder()
    hunk = builder.build("docs/note.md", "# Old\n", "# New", ["e1"])
    assert hunk is not None
    assert hunk.original == "# Old"
    assert builder.build("docs/note.md", "", "# New", ["e1"]) is None
