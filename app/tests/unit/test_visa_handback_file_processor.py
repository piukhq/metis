import os
from unittest.mock import patch

from pyfakefs import fake_filesystem_unittest

import settings
from app.visa_handback_file_processor import get_dir_contents, mkdir_p, VisaHandback


def setup_encrypted_file():
    file = 'LOYANG_REG_PAN_1483460158.LOYANG_RESP.D170103.pgp'
    path = '../fixtures/' + file
    with open(path, 'rb') as gpg_file:
        encrypted_file = gpg_file.read()
        return path, encrypted_file


class TestVisaHandback(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.path, self.encrypted_file = setup_encrypted_file()
        self.setUpPyfakefs()

    @patch('app.visa_handback_file_processor.scandir')
    def test_get_dir_contents(self, mock_scandir):
        mock_scandir.side_effect = self.fs.ScanDir
        '''Test visa_handback_file_processor.dir_exists()'''
        # The os module has been replaced with the fake os module so all of the
        # following occurs in the fake filesystem.
        mkdir_p('../fixtures')
        self.assertTrue(os.path.isdir('../fixtures'))
        # This is the equivalent of `touch` on unix
        if self.path and self.encrypted_file:
            with open(self.path, 'wb') as test_gpg_file:
                test_gpg_file.write(self.encrypted_file)
        payment_files = get_dir_contents('../fixtures')
        self.assertIsInstance(payment_files, list)
        self.assertEqual(len(payment_files), 1)
        self.assertTrue(payment_files[0].endswith('pgp'))

    def test_mkdir_p(self):
        dir = 'test_dir/test_subdir'
        mkdir_p(dir)
        self.assertTrue(os.path.isdir(dir))

    def test_bink_error_lookup(self):
        code = '4'
        v = VisaHandback()
        state, err_string = v.bink_error_lookup(code)
        self.assertTrue(type(state) is bool)
        self.assertTrue(type(err_string) is str)

    @patch('app.visa_handback_file_processor.scandir')
    def test__decrypt_file(self, mock_scandir):
        mock_scandir.side_effect = self.fs.ScanDir
        mkdir_p('../fixtures')
        if self.path and self.encrypted_file:
            with open(self.path, 'wb') as test_gpg_file:
                test_gpg_file.write(self.encrypted_file)
        v = VisaHandback()
        payment_files = get_dir_contents('../fixtures')
        self.assertTrue(len(payment_files))
        for encrypted_file in payment_files:
            if encrypted_file.endswith(v.gpg_file_ext):
                output_file_name = v._decrypt_file(encrypted_file)
                self.assertTrue(len(output_file_name))

    def test_archive_files(self):
        filename = 'afile.txt'
        mkdir_p('../fixtures')
        touched_file = '../fixtures/' + filename
        with open(touched_file, 'a'):
            os.utime(touched_file, None)
        v = VisaHandback()
        v.archive_files(touched_file)
        result = os.path.isfile(settings.VISA_ARCHIVE_DIR + '/' + filename)
        self.assertTrue(result)

    def test_perform_file_archive(self):
        filename = 'afile.txt'
        mkdir_p('../fixtures')
        touched_file = '../fixtures/' + filename
        with open(touched_file, 'a'):
            os.utime(touched_file, None)
        v = VisaHandback()
        v.perform_file_archive(touched_file, settings.VISA_ARCHIVE_DIR)
        result = os.path.isfile(settings.VISA_ARCHIVE_DIR + '/' + filename)
        self.assertTrue(result)

    @patch('app.visa_handback_file_processor.scandir')
    def test_file_list(self, mock_scandir):
        mock_scandir.side_effect = self.fs.ScanDir
        v = VisaHandback()
        mkdir_p('../fixtures')
        if self.path and self.encrypted_file:
            with open(self.path, 'wb') as test_gpg_file:
                test_gpg_file.write(self.encrypted_file)
        payment_files = get_dir_contents('../fixtures')
        txt_files = v.file_list(payment_files)
        self.assertTrue(len(txt_files))

if __name__ == '__main__':
    path, encrypted_file = setup_encrypted_file()