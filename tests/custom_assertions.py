class CustomAssertions:
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
