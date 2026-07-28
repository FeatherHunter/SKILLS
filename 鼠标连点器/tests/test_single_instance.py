import os
import pytest

@pytest.mark.skipif(os.name != "nt", reason="Windows-only")
def test_acquire_then_second_acquire_fails():
    from src.single_instance import SingleInstance
    si1 = SingleInstance(name="Local\\AutoClickerSingleInstance_TEST_A")
    si2 = SingleInstance(name="Local\\AutoClickerSingleInstance_TEST_A")
    assert si1.acquire()
    assert not si2.acquire()
    si1.release()
    assert si2.acquire()
    si2.release()
