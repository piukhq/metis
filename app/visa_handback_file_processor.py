import os
import errno
import shutil
import subprocess

from scandir import scandir

import settings


class VisaHandback(object):
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

        if return_code in bink_code_lookup.keys():
            return True, bink_code_lookup[return_code]
        else:
            return False, 'None'

    def read_handback_file(self, payment_files):
        rows = 0
        txt_files = self.file_list(payment_files)
        bink_rows = 0
        first_row = True

        for txt_file in txt_files:
            with open(txt_file) as file:
                for row in file:
                    if first_row:
                        first_row = False
                        continue
                    token_field = (63, 88)
                    token = row[token_field[0]:token_field[1]].strip()
                    return_code_field = (741, 745)
                    return_code = row[return_code_field[0]:return_code_field[1]].strip()
                    return_description_field = (745, 1000)
                    return_description = row[return_description_field[0]:return_description_field[1]].strip()

                    bink_row, bink_error_text = self.bink_error_lookup(return_code)
                    if return_description:
                        if bink_row:
                            bink_rows += 1
                            settings.logger.info("{} {} {}".format(token, return_code, bink_error_text))
                        else:
                            settings.logger.info("{} {} {}".format(token, return_code, return_description))
                    rows += 1

                settings.logger.info("Filename: {}, Number of rows: {}, Number of rows requiring action by "
                                     "Bink: {}".format(txt_file, rows-1, bink_rows))
                self.archive_files(txt_file)
        return rows

    def file_list(self, payment_files):
        txt_files = [self._decrypt_file(encrypted_file) for encrypted_file in payment_files
                     if (encrypted_file.endswith(self.gpg_file_ext) and os.path.isfile(encrypted_file))]
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


def get_dir_contents(src_dir):
    files = []
    for entry in scandir(src_dir):
        if entry.is_file(follow_symlinks=False):
            files.append(entry.path)

    return files


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


if __name__ == '__main__':
    v = VisaHandback()
    payment_files = get_dir_contents(settings.VISA_SOURCE_FILES_DIR)
    v.read_handback_file(payment_files)
