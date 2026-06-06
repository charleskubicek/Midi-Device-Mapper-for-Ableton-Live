from ableton_control_surface_as_code.gen_error import GenError


class CustomAssertions:
    def assert_gen_error(self, fn, code=None, *must_contain):
        """Assert fn() raises a GenError (not a raw Lark/Pydantic/ValueError leak).

        Optionally asserts the error_code and that the message contains each of
        ``must_contain`` (substring match, so wording can still improve freely).
        """
        try:
            fn()
        except GenError as e:
            msg = str(e)
            if code is not None and e.error_code != int(code):
                raise self.failureException(
                    f"expected error_code {int(code)}, got {e.error_code}: {msg}")
            for frag in must_contain:
                if frag not in msg:
                    raise self.failureException(f"'{frag}' not in error message: {msg}")
            return e
        except Exception as e:
            raise self.failureException(
                f"expected GenError, got {type(e).__name__}: {e}")
        raise self.failureException("expected GenError, but no exception was raised")

    def assert_string_in(self, sub, st):
        if sub not in st:
            raise self.failureException(f"{sub} not in {st}")


    def assert_string_in_one(self, sub, sts:[str]):
        found = False
        for st in sts:
            if sub in st:
                return

        if not found:
            raise self.failureException(f"{sub} not in {sts}")
