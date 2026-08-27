import io

from sale_dashboard.__main__ import make_progress_logger


def test_progress_logger_flushes_action_visible_lines():
    output = io.StringIO()
    logger = make_progress_logger(output)

    logger('projects page 1')

    assert output.getvalue() == '[sale-dashboard] projects page 1\n'
