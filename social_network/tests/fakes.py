class FakeCursor:
    def __init__(self, accepted_rows=5):
        self.accepted_rows = accepted_rows
        self.executed = []
        self.copied = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return (self.accepted_rows,)

    def copy(self, sql, data):
        self.copied.append((sql, data))


class FakeConnection:
    def __init__(self, accepted_rows=5):
        self._cursor = FakeCursor(accepted_rows)
        self.commits = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1
