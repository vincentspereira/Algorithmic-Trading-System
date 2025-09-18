# Pytest configuration and helpers for unit tests
# This autouse fixture injects a sample_message attribute into TestMessageRouting
# to satisfy tests that reference self.sample_message without defining it locally.

import time
import pytest


@pytest.fixture(autouse=True)
def _inject_sample_message(request):
    inst = getattr(request, "instance", None)
    if inst and inst.__class__.__name__ == "TestMessageRouting" and not hasattr(inst, "sample_message"):
        inst.sample_message = {
            'id': 'msg_001',
            'type': 'market_data',
            'timestamp': time.time(),
            'data': {
                'symbol': 'EURUSD',
                'bid': 1.0850,
                'ask': 1.0852,
                'volume': 1000000,
            },
        }
    # No return; fixture is for side effects only