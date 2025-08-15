import re
from decOM.__main__ import _version

def test_version_format():
    v = _version()
    # Basic pattern: base semantic-ish version plus optional suffix after a dash
    assert re.match(r'^\d+\.\d+\.\d+($|-.+)', v), f"Unexpected version format: {v}"
