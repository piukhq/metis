import os
import re
import json
from unittest.mock import patch

import httpretty
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
    auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
               'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'

    def hermes_provider_status_mappings_route(self):
        httpretty.register_uri(httpretty.GET,
                               re.compile('{}/payment_cards/provider_status_mappings/(.+)'.format(settings.HERMES_URL)),
                               status=200,
                               headers={'Authorization': self.auth_key},
                               body=json.dumps([{'provider_status_code': 'BINK_UNKNOWN',
                                                 'bink_status_code': 10}]),
                               content_type='application/json')

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
        # make the list order predictable
        payment_files.sort()
        self.assertIsInstance(payment_files, list)
        # There should be the 'afile.txt' and the fixture file so two files in the directory.
        self.assertEqual(len(payment_files), 2)
        self.assertTrue(payment_files[0].endswith('pgp'))

    @httpretty.activate
    def test_bink_error_lookup(self):
        self.hermes_provider_status_mappings_route()
        v = VisaHandback()
        err_code = v.bink_error_lookup(self.code)
        self.assertIsInstance(err_code, int)

    @httpretty.activate
    def test_archive_files(self):
        self.hermes_provider_status_mappings_route()
        v = VisaHandback()
        v.archive_files(self.touched_file)
        result = os.path.isfile(settings.VISA_ARCHIVE_DIR + '/' + self.filename)
        self.assertTrue(result)

    @httpretty.activate
    def test_perform_file_archive(self):
        self.hermes_provider_status_mappings_route()
        v = VisaHandback()
        v.perform_file_archive(self.touched_file, settings.VISA_ARCHIVE_DIR)
        result = os.path.isfile(settings.VISA_ARCHIVE_DIR + '/' + self.filename)
        self.assertTrue(result)
