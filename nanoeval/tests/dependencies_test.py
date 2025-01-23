import oaipkg


def test_dependencies() -> None:
    assert set(oaipkg.get_monorepo_project("nanoeval").monorepo_dependencies) == {
        "chz",
    }
