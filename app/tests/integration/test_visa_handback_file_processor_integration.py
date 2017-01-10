import os
import mock
from pyfakefs import fake_filesystem_unittest
# The module under test is pyfakefs.visa_handback_file_processor
from scandir import scandir

import settings
from app.visa_handback_file_processor import get_dir_contents, mkdir_p, VisaHandback


def scandir_function():
    pass

class TestVisaHandback(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()

    def tearDown(self):
        # It is no longer necessary to add self.tearDownPyfakefs()
        pass

    @mock.patch('app.visa_handback_file_processor.scandir', side_effect=scandir)
    def test_import_transactions(self, scandir_function):
        payment_files = get_dir_contents('../../' + settings.VISA_SOURCE_FILES_DIR)
        self.assertTrue(len(payment_files))
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
