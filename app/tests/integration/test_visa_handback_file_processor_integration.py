import os
from unittest.mock import patch
from pyfakefs import fake_filesystem_unittest
# The module under test is pyfakefs.visa_handback_file_processor

import settings
from app.visa_handback_file_processor import get_dir_contents, mkdir_p, VisaHandback


fixture_path = os.path.join(settings.APP_DIR, 'app/tests/fixtures/')


def setup_encrypted_file():
    file = 'LOYANG_REG_PAN_1483460158.LOYANG_RESP.D170103.pgp'
    path = fixture_path + file
    with open(path, 'rb') as gpg_file:
        encrypted_file = gpg_file.read()
        return path, encrypted_file


class TestVisaHandback(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.path, self.encrypted_file = setup_encrypted_file()
        self.setUpPyfakefs()

    @patch('app.visa_handback_file_processor.scandir')
    def test_read_handback_file(self, mock_scandir):
        mock_scandir.side_effect = self.fs.ScanDir
        mkdir_p(fixture_path)
        with open(self.path, 'wb') as test_gpg_file:
            test_gpg_file.write(self.encrypted_file)
        payment_files = get_dir_contents(fixture_path)
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
