import os
import unittest
from pyfakefs import fake_filesystem_unittest
# The module under test is pyfakefs.visa_handback_file_processor
import settings
from app.visa_handback_file_processor import get_dir_contents, mkdir_p


class TestVisaHandback(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()

    def tearDown(self):
        # It is no longer necessary to add self.tearDownPyfakefs()
        pass

    def test_get_dir_contents(self):
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


if __name__ == '__main__':
    unittest.main()
