"""`config.transactions`: re-running a MongoDB transaction that lost a conflict."""

import pytest
from django.db import DatabaseError, IntegrityError

from config import transactions


class _Conflict(DatabaseError):
    """Looks like what Django raises for MongoDB's `TransientTransactionError`."""

    def __init__(self):
        super().__init__("write conflict")
        cause = mock_cause()
        self.__cause__ = cause


def mock_cause():
    class Cause(Exception):
        @staticmethod
        def has_error_label(label):
            return label == "TransientTransactionError"

    return Cause()


@pytest.mark.django_db(transaction=True)
class TestRunAtomic:
    def test_a_lost_conflict_is_run_again_and_the_second_result_is_returned(self):
        calls = []

        def body():
            calls.append(1)
            if len(calls) == 1:
                raise _Conflict()
            return "second try"

        assert transactions.run_atomic(body) == "second try"
        assert len(calls) == 2

    def test_an_ordinary_database_error_is_not_retried(self):
        calls = []

        def body():
            calls.append(1)
            raise DatabaseError("not a conflict")

        with pytest.raises(DatabaseError):
            transactions.run_atomic(body)
        assert len(calls) == 1

    def test_a_conflict_that_never_clears_gives_up_after_the_attempts(self):
        calls = []

        def body():
            calls.append(1)
            raise _Conflict()

        with pytest.raises(DatabaseError):
            transactions.run_atomic(body, attempts=3)
        assert len(calls) == 3

    def test_extra_errors_can_be_declared_retryable(self):
        calls = []

        def body():
            calls.append(1)
            if len(calls) == 1:
                raise IntegrityError("duplicate key")
            return "recomputed"

        assert transactions.run_atomic(body, also_retry=(IntegrityError,)) == "recomputed"
        assert len(calls) == 2

    def test_inside_an_outer_transaction_the_body_runs_once_and_the_outer_one_retries(self):
        inner_calls = []

        def inner():
            inner_calls.append(1)
            raise _Conflict()

        def outer():
            transactions.run_atomic(inner)

        with pytest.raises(DatabaseError):
            transactions.run_atomic(outer, attempts=2)
        # Two attempts of the OUTER block, one run of the inner body in each.
        assert len(inner_calls) == 2

    def test_the_decorator_passes_arguments_and_keeps_the_name(self):
        @transactions.atomic_retrying
        def add(a, b=0):
            return a + b

        assert add(2, b=3) == 5
        assert add.__name__ == "add"
