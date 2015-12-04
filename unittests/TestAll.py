import os
import unittest
os.environ['UNITTESTING'] = 'True'
from unittests.PreProcessingTester import TestRnaCountsProcessor
from unittests.LoggerTester import TestLogs
from unittests.UtilitiesTester import GdfExportTester, LinalgRoutinesTester, SanerFilesystemTester
from unittests.ParserTester import GoParserTester, UniprotParserTester


class HooksConfigTest(unittest.TestCase):

    def test_hooks(self):
        self.assertTrue(True)

    def test_actual_code(self):
        from BioFlow.main_configs import edge_type_filters
        self.assertEqual(edge_type_filters["Group"][0], "is_part_of_collection")


if __name__ == "__main__":
    mylist = [TestRnaCountsProcessor.__doc__, TestLogs.__doc__, GdfExportTester.__doc__,
              LinalgRoutinesTester.__doc__, SanerFilesystemTester.__doc__, GoParserTester.__doc__,
              UniprotParserTester.__doc__]
    unittest.main()
