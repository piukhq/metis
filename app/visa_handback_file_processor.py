import os
import shutil
import subprocess

from scandir import scandir

from app.hermes import get_provider_status_mapping, put_account_status
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
        self.bink_code_lookup = get_provider_status_mapping('visa')

    def bink_error_lookup(self, return_code):
        if return_code in self.bink_code_lookup.keys():
            return self.bink_code_lookup[return_code]
        else:
            return self.bink_code_lookup['BINK_UNKNOWN']

    def read_handback_file(self, payment_files):
        txt_files = self.file_list(payment_files)
        bink_rows = 0

        token_field = (63, 88)
        return_code_field = (741, 745)
        return_description_field = (745, 1000)

        for txt_file in txt_files:
            with open(txt_file) as file:
                for row in file:
                    # This ensures the header and footer are ignored.
                    if row[:2] == '00' or row[:2] == '99':
                        continue

                    token = row[token_field[0]:token_field[1]].strip()
                    return_code = row[return_code_field[0]:return_code_field[1]].strip()
                    return_description = row[return_description_field[0]:return_description_field[1]].strip()

                    bink_status = self.bink_error_lookup(return_code)

                    bink_rows += 1
                    put_account_status(bink_status, token=token)
                    settings.logger.info("{} {} {}".format(token, return_code, return_description))

                settings.logger.info("Filename: {}, Number of rows requiring action by "
                                     "Bink: {}".format(txt_file, bink_rows))
                self.archive_files(txt_file)

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


if __name__ == '__main__':
    v = VisaHandback()
    payment_files = get_dir_contents(settings.VISA_SOURCE_FILES_DIR)
    v.read_handback_file(payment_files)
