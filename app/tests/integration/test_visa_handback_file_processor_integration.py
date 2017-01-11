import os
import unittest

import settings
from app.visa_handback_file_processor import get_dir_contents, mkdir_p, VisaHandback


fixture_path = os.path.join(settings.APP_DIR, 'app/tests/fixtures/')


class TestVisaHandback(unittest.TestCase):
    def test_read_handback_file(self):
        payment_files = get_dir_contents(fixture_path)
        mkdir_p(settings.VISA_ARCHIVE_DIR)
        target_files = get_dir_contents(settings.VISA_ARCHIVE_DIR)
        if len(target_files):
            for target_file in target_files:
                if os.path.isfile(target_file):
                    os.remove(target_file)
        v = VisaHandback()
        v.read_handback_file(payment_files)
        target_files = get_dir_contents(settings.VISA_ARCHIVE_DIR)
        self.assertTrue(len(target_files))
