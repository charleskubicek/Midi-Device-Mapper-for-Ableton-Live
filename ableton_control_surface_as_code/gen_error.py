from enum import IntEnum


class ErrorCode(IntEnum):
    """Stable error codes for config problems surfaced to the user.

    Code 1 (CLASHING_MAPPINGS) predates this enum and is kept for back-compat.
    """
    CLASHING_MAPPINGS = 1
    COORD_SYNTAX = 2
    CONFIG_VALIDATION = 3
    SEMANTIC_VALIDATION = 4


class GenError(Exception):
    def __init__(self, message, error_code: int):
        super().__init__(message)
        self.error_code = int(error_code)


class ProblemAccumulator:
    """Collects config problems so a generation run can report them all at once
    instead of failing on the first.

    Phase 1 Workstream C: the semantic validators (controller MIDI ranges, mode
    names, mapping clashes, coord resolution) each used to raise on the first
    problem, hiding the rest. They now append into a shared accumulator that the
    top-level orchestrator (`build_validated_model`) raises once, after every
    check has had a chance to run. Accumulation only spans checks that can run
    on successfully-parsed input — a parse failure still raises immediately,
    since there is nothing left to validate.
    """

    def __init__(self):
        self._problems = []

    def add(self, message: str) -> None:
        self._problems.append(message)

    def extend(self, messages) -> None:
        self._problems.extend(messages)

    def capture(self, fn, *, default=None):
        """Run ``fn``; if it raises a GenError, record it and return ``default``
        so sibling checks can still run. Non-GenError exceptions propagate."""
        try:
            return fn()
        except GenError as e:
            self._problems.append(str(e))
            return default

    @property
    def problems(self):
        return list(self._problems)

    def raise_if_any(self, code=ErrorCode.SEMANTIC_VALIDATION) -> None:
        if self._problems:
            n = len(self._problems)
            body = "\n".join(f"  {i}. {p}" for i, p in enumerate(self._problems, 1))
            raise GenError(f"Found {n} config problem(s):\n{body}", code)

