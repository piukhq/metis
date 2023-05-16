import os
import unittest
from pathlib import Path

from metis import settings
from metis.visa_handback_file_processor import VisaHandback, get_dir_contents

fixture_path = os.path.join(settings.APP_DIR, "app/tests/fixtures/")


class TestVisaHandback(unittest.TestCase):
    def test_read_handback_file(self):
        payment_files = get_dir_contents(fixture_path)
        Path(settings.VISA_ARCHIVE_DIR).mkdir(parents=True, exist_ok=True)
        target_files = get_dir_contents(settings.VISA_ARCHIVE_DIR)
        if len(target_files):
            for target_file in target_files:
                if os.path.isfile(target_file):
                    Path(target_file).unlink()
        v = VisaHandback()
        v.read_handback_file(payment_files)
        target_files = get_dir_contents(settings.VISA_ARCHIVE_DIR)
        self.assertTrue(len(target_files))
