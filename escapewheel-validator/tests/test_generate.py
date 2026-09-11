

def test_a_tree_digest_does_not_depend_on_enumeration_order(tmp_path):
    """`04` §5.4 sorts the member keys, which is what makes the digest reproducible.

    Two implementations enumerate an object-store prefix and a local directory in different
    orders; a digest that folded them in arrival order would disagree between them.
    """
    from escapewheel_validator.stores import digest

    prefix = tmp_path / "array.zarr"
    (prefix / "c").mkdir(parents=True)
    for name, body in (("zarr.json", b"{}"), ("c/0", b"aaa"), ("c/1", b"bb"), ("c/2", b"c")):
        (prefix / name).write_bytes(body)
    first = digest(str(prefix))

    # Re-create in the opposite order; the listing the digest is taken over must not care.
    import shutil

    shutil.rmtree(prefix)
    (prefix / "c").mkdir(parents=True)
    for name, body in (("c/2", b"c"), ("c/1", b"bb"), ("c/0", b"aaa"), ("zarr.json", b"{}")):
        (prefix / name).write_bytes(body)
    assert digest(str(prefix)) == first


def test_changing_one_member_changes_the_tree_digest(tmp_path):
    """A digest that missed a chunk edit would make R52's immutability premise unfalsifiable."""
    from escapewheel_validator.stores import digest

    prefix = tmp_path / "array.zarr"
    prefix.mkdir()
    (prefix / "zarr.json").write_bytes(b"{}")
    (prefix / "chunk").write_bytes(b"aaa")
    before = digest(str(prefix))
    (prefix / "chunk").write_bytes(b"aab")
    assert digest(str(prefix)) != before


def test_adding_a_member_changes_the_tree_digest(tmp_path):
    """`04` §5.4: the declared members and the digested listing cannot disagree."""
    from escapewheel_validator.stores import digest

    prefix = tmp_path / "array.zarr"
    prefix.mkdir()
    (prefix / "zarr.json").write_bytes(b"{}")
    before = digest(str(prefix))
    (prefix / "extra").write_bytes(b"")
    assert digest(str(prefix)) != before
