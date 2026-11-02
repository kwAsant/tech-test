import io
import unittest
from contextlib import redirect_stdout

from techtest.models import ScalarResults
from techtest.risk_system import ScreenResultPrinter


class ScreenResultPrinterTests(unittest.TestCase):
    def test_prints_results_and_errors_for_each_trade(self):
        results = ScalarResults()
        results.add_result('both', 12.5)
        results.add_error('both', 'warning')
        results.add_result('zero', 0.0)
        results.add_error('error', 'failed')
        output = io.StringIO()

        with redirect_stdout(output):
            ScreenResultPrinter().print_results(results)

        self.assertEqual(output.getvalue().splitlines(), [
            'both : 12.5 : warning',
            'zero : 0.0',
            'error : failed',
        ])


if __name__ == '__main__':
    unittest.main()
