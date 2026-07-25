import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import render_body_composition_wizard as rbcw
from pathlib import Path


def test_render_creates_file_with_data():
    fd, tmp = tempfile.mkstemp(suffix='.html'); os.close(fd)
    Path(tmp).unlink()
    result = rbcw.render(Path(tmp))
    assert result.exists()
    content = result.read_text(encoding='utf-8')
    assert '__DATA__' in content
    assert 'window.__DATA__ = ' in content
    assert 'fetched_at' in content
    os.unlink(tmp)


def test_emit_send_protocol_prints_warning():
    import io, sys
    captured = io.StringIO()
    sys.stdout = captured
    try:
        rbcw.emit_send_protocol(Path('/tmp/test.html'))
    finally:
        sys.stdout = sys.__stdout__
    assert 'ACTION=SEND_TO_USER' in captured.getvalue()
    assert '/tmp/test.html' in captured.getvalue()
