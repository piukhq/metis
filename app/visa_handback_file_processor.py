import os
import shutil
import subprocess
from collections import OrderedDict

from handylib.fixedcolumnfile import FixedColumnFileReader

import settings


class VisaHandback(object):

    columns = OrderedDict([
        ('record_type', 2),
        ('record_subtype', 2),
        ('promotion_type', 2),
        ('promotion_code', 25),
        ('action_code', 1),
        ('endpoint_code', 6),
        ('promotion_group_id', 6),
        ('cardholder_account_number', 19),
        ('external_cardholder_id', 25),
        ('effective_date', 8),
        ('termination_date', 8),
        ('filler', 503),
        ('return_code', 4),
        ('return_description', 255),
    ])

    column_keep = {
        'external_cardholder_id': 'external_cardholder_id',
        'return_description': 'return_description',
    }

    field_delete = [
        'record_type',
        'record_subtype',
        'promotion_type',
        'promotion_code',
        'action_code',
        'endpoint_code',
        'promotion_group_id',
        'cardholder_account_number',
        'external_cardholder_id',
        'effective_date',
        'termination_date',
        'filler',
    ]

    # useful to find and fetch transaction files
    file_extension = '.txt'
    plain_text_file_extension = '.VISA'

    def __init__(self,
                 keyring=settings.VISA_KEYRING_DIR,
                 archive_dir=settings.VISA_ARCHIVE_DIR,
                 gpg_file_ext=settings.VISA_ENCRYPTED_FILE_EXTENSION):

        self.keyring = keyring
        self.archive_dir = archive_dir
        self.gpg_file_ext = gpg_file_ext
        self.text_file_suffix = '.unencrypted.txt'

    def bink_error_lookup(self, return_code):
        """It is anticipated that this function will call (possibly indirectly) hermes with a requests call to
        obtain the dict of bink error messages based on code lookups for visa"""

        bink_code_lookup = {
            '514': 'This is an example Bink lookup error message',
        }

        if str(return_code).strip() in bink_code_lookup.keys():
            return True, bink_code_lookup[str(return_code).strip()]
        else:
            return False, 'None'

    def import_transactions(self, payment_files):
        rows = 0
        reader = FixedColumnFileReader(self.columns, self.column_keep)
        txt_files = self.file_list(payment_files)
        bink_rows = 0

        for txt_file in txt_files:
            for row in reader(txt_file):
                log_string = []
                description_found = False
                token_found = False
                for col in self.column_keep:
                    if col in row.keys():
                        if col == 'return_description':
                            bink_row, bink_error_text = self.bink_error_lookup(row[str(col)][:4])
                            if bink_row:
                                log_string.append(row[str(col)][:4].strip())
                                log_string.append(bink_error_text)
                                bink_rows += 1
                            else:
                                log_string.append(row[str(col)])
                            description_found = True
                        else:
                            log_string.append(row[str(col)])
                            token_found = True

                    if description_found and token_found:
                        if len(log_string[0]):
                            settings.logger.info("{}".format(' '.join(log_string)))

                rows += 1
            settings.logger.info("Filename: {}, Number of rows: {}, Number of rows requiring action by Bink: {}".format(txt_file, rows-1, bink_rows))
            # self.archive_files(txt_file)
        return rows

    def file_list(self, payment_files):
        txt_files = [self._decrypt_file(encrypted_file) for encrypted_file in payment_files
                     if encrypted_file.endswith(self.gpg_file_ext) or
                     encrypted_file.endswith(self.plain_text_file_extension)
                     # Kafka cannot guarantee the import file has already been processed
                     #  so filter out any files in the archive directory
                     if os.path.isfile(encrypted_file)]
        return txt_files

    @staticmethod
    def perform_file_archive(source_file, archive_dir):
        os.makedirs(archive_dir, exist_ok=True)
        archive_file_path = os.path.join(archive_dir, os.path.basename(source_file))
        if not os.path.exists(archive_file_path):
            shutil.move(source_file, archive_dir)
        else:
            os.remove(source_file)

    def archive_files(self, txt_file):
        self.perform_file_archive(txt_file, self.archive_dir)
        if txt_file.endswith(self.text_file_suffix):
            self.perform_file_archive(txt_file[:-len(self.text_file_suffix)], self.archive_dir)

    def _decrypt_file(self, encrypted_file):
        """
        Decrypt file using GPG.
        There is a bug in the current gnupg python package so using subprocess instead.
        See: https://bitbucket.org/vinay.sajip/python-gnupg/issues/11/decryption-of-files-in-binary-format-fails
        :param encrypted_file:
        :return:
        """""
        try:
            # Special case: Visa send plain transaction files to Bink where a problem occurred in the normal
            # encrypted file process. We manually add the .VISA extension to these plain text files to
            # differentiate from other files in the Visa directory.
            if encrypted_file[-5:] == ".VISA":
                output_file_name = encrypted_file
            else:
                output_file_name = encrypted_file + self.text_file_suffix
                # If the output file exists GPG will fail so handle this case
                if os.path.exists(output_file_name):
                    os.remove(output_file_name)

                gpg_args = [
                    "gpg",
                    "--homedir",
                    self.keyring,
                    "--output",
                    output_file_name,
                    "--decrypt",
                    encrypted_file]

                # The check parameter means subprocess raises an exception if return value != 0
                subprocess.check_call(gpg_args, timeout=2)

            return output_file_name
        except(subprocess.SubprocessError, OSError, ValueError) as gpg_error:
            error_msg = "Error decrypting Visa File using GPG {}".format(str(gpg_error))
            settings.logger.error(error_msg)
            raise


if __name__ == '__main__':
    v = VisaHandback()
    payment_files = ['/home/oe/Downloads/metis_visa/LOYANG_REG_PAN_1483460158.LOYANG_RESP.D170103.pgp', ]
    v.import_transactions(payment_files)
