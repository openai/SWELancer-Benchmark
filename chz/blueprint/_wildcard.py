import re

_FUZZY_SIMILARITY = 0.6


def wildcard_key_to_regex(key: str) -> re.Pattern[str]:
    if key.endswith("..."):
        raise ValueError("Wildcard not allowed at end of key")
    pattern = r"(.*\.)?" if key.startswith("...") else ""
    pattern += r"\.(.*\.)?".join(map(re.escape, key.removeprefix("...").split("...")))
    return re.compile(pattern)


def _wildcard_key_match(key: str, target_str: str) -> bool:
    # This is what the regex does; currently unused (but is tested)
    if key.endswith("..."):
        raise ValueError("Wildcard not allowed at end of key")
    pattern = ["..."] if key.startswith("...") else []
    pattern += [x for x in re.split(r"(\.\.\.)|\.", key.removeprefix("...")) if x is not None]
    target = target_str.split(".")

    _grid: dict[tuple[int, int], bool] = {}

    def _match(i: int, j: int) -> bool:
        if i == len(pattern):
            return j == len(target)
        if j == len(target):
            return False
        if (i, j) in _grid:
            return _grid[i, j]
        if pattern[i] == "...":
            ret = _match(i, j + 1) or _match(i + 1, j)
            _grid[i, j] = ret
            return ret
        ret = pattern[i] == target[j] and _match(i + 1, j + 1)
        _grid[i, j] = ret
        return ret

    return _match(0, 0)


def wildcard_key_approx(key: str, target_str: str) -> tuple[float, str]:
    """
    Returns a score and a string representing what the key should have been to match the target.

    Currently only used in error messages.
    """
    if key.endswith("..."):
        raise ValueError("Wildcard not allowed at end of key")
    pattern = ["..."] if key.startswith("...") else []
    pattern += [x for x in re.split(r"(\.\.\.)|\.", key.removeprefix("...")) if x is not None]
    target = target_str.split(".")

    import difflib

    _grid: dict[tuple[int, int], tuple[float, tuple[str, ...]]] = {}

    def _match(i, j) -> tuple[float, tuple[str, ...]]:
        if i == len(pattern):
            return (1, ()) if j == len(target) else (0, ())
        if j == len(target):
            return (0, ())
        if (i, j) in _grid:
            return _grid[i, j]
        if pattern[i] == "...":
            with_wildcard = _match(i, j + 1)
            without_wildcard = _match(i + 1, j)
            if with_wildcard[0] * _FUZZY_SIMILARITY > without_wildcard[0]:
                score, value = with_wildcard
                score *= _FUZZY_SIMILARITY
            else:
                score, value = without_wildcard
            if value and value[0] != "...":
                value = ("...",) + value
            ret = (score, value)
            _grid[i, j] = ret
            return ret

        ratio = difflib.SequenceMatcher(a=pattern[i], b=target[j]).ratio()
        if ratio >= _FUZZY_SIMILARITY:
            score, value = _match(i + 1, j + 1)
            score *= ratio
            if value and value[0] != "...":
                value = (target[j] + ".",) + value
            else:
                value = (target[j],) + value
            ret = (score, value)
            _grid[i, j] = ret
            return ret
        return 0, ()

    score, value = _match(0, 0)
    return score, "".join(value)
