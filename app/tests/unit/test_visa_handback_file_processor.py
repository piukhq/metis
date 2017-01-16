import os
from unittest.mock import patch

from pyfakefs import fake_filesystem_unittest

import settings
from app.visa_handback_file_processor import get_dir_contents, VisaHandback


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
        self.code = '4'
        os.makedirs(fixture_path, exist_ok=True)
        self.filename = 'afile.txt'
        self.touched_file = fixture_path + self.filename
        with open(self.touched_file, 'a'):
            os.utime(self.touched_file, None)

    @patch('app.visa_handback_file_processor.scandir')
    def test_get_dir_contents(self, mock_scandir):
        mock_scandir.side_effect = self.fs.ScanDir
        '''Test visa_handback_file_processor.dir_exists()'''
        # The os module has been replaced with the fake os module so all of the
        # following occurs in the fake filesystem.
        self.assertTrue(os.path.isdir(fixture_path))
        # This is the equivalent of `touch` on unix
        with open(self.path, 'wb') as pgp_file:
            pgp_file.write(self.encrypted_file)
        payment_files = get_dir_contents(fixture_path)
        self.assertIsInstance(payment_files, list)
        print(len(payment_files), payment_files)
        self.assertEqual(len(payment_files), 1)
        self.assertTrue(payment_files[0].endswith('pgp'))

    def test_bink_error_lookup(self):
        v = VisaHandback()
        state, err_string = v.bink_error_lookup(self.code)
        self.assertTrue(type(state) is bool)
        self.assertTrue(type(err_string) is str)

    def test_archive_files(self):
        v = VisaHandback()
        v.archive_files(self.touched_file)
        result = os.path.isfile(settings.VISA_ARCHIVE_DIR + '/' + self.filename)
        self.assertTrue(result)

    def test_perform_file_archive(self):
        v = VisaHandback()
        v.perform_file_archive(self.touched_file, settings.VISA_ARCHIVE_DIR)
        result = os.path.isfile(settings.VISA_ARCHIVE_DIR + '/' + self.filename)
        self.assertTrue(result)
