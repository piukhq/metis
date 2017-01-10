import os
import mock
from pyfakefs import fake_filesystem_unittest
# The module under test is pyfakefs.visa_handback_file_processor
from scandir import scandir

import settings
from app.visa_handback_file_processor import get_dir_contents, mkdir_p


def scandir_function(path=''):
    return ['./']


class TestVisaHandback(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()

    def tearDown(self):
        # It is no longer necessary to add self.tearDownPyfakefs()
        pass

    @mock.patch('app.visa_handback_file_processor.scandir', side_effect=scandir)
    def test_get_dir_contents(self, scandir_function):
        '''Test visa_handback_file_processor.dir_exists()'''
        # The os module has been replaced with the fake os module so all of the
        # following occurs in the fake filesystem.
        mkdir_p('../../' + settings.VISA_SOURCE_FILES_DIR)
        self.assertTrue(os.path.isdir('../../' + settings.VISA_SOURCE_FILES_DIR))
        # This is the equivalent of `touch` on unix
        touched_file = '../../' + settings.VISA_SOURCE_FILES_DIR + '/afile.txt'
        with open(touched_file, 'a'):
            os.utime(touched_file, None)
        payment_files = get_dir_contents('../../' + settings.VISA_SOURCE_FILES_DIR)
        self.assertTrue(len(payment_files))
