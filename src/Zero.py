from cmd import Cmd
import sys
import threading

import getpass
import shutil
import os
import src.Utils as Utils
from src.LogLib import LogLib


from ftplib import FTP
# TODO: cleaner way of defining sys path or posix and nt

VERSION = "0.1-(Beta)"
TIMESTAMP = "June'18"

# parent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
# sys.path.append(parent_path)

# from src.utils import Utils
# from src.loglib import LogLib

# CONSTANTS
NUM_PARTS = 20
BLOCK_SIZE = 1024000
DOMAIN = ""
SERVER_NAME = ""
FULL_SERVER_NAME = ""
AUTHOR = ""

logger = LogLib.get_logger()


class Download:

    def __init__(self, server_specs, file_name="", output_directory="", md5=None):

        self.__server_specs = server_specs
        self.__server = server_specs["Server"]
        self.__user_id = server_specs["UserId"]
        self.__password = server_specs["Password"]
        self.__port = server_specs["Port"]
        self.__working_dir = server_specs["WorkingDirectory"]

        self.output_directory = output_directory
        self.__download_directory = os.path.join(output_directory, "tmp")
        if os.path.exists(self.__download_directory):
            shutil.rmtree(self.__download_directory)
            # Utils.delete_folder(self.__download_directory)
        os.makedirs(self.__download_directory)

        self.output_path = None
        self.file_name = file_name

        self.md5 = md5
        self.file_size = None

        self.__parts_list = list()
        self.__part_size = None
        self.__final_part_size = None

        self.__set_file_size()
        self.__set_parts_size()
        self.__set_output_path()

    def __set_parts_size(self):
        try:
            logger.debug("Setting part-size")
            if self.file_size is None:
                self.__set_file_size()

            self.__part_size = int(self.file_size/NUM_PARTS)
            self.__final_part_size = self.file_size - self.__part_size*(NUM_PARTS - 1)

            logger.debug("Part size set to : {}".format(self.__part_size))
            logger.debug("Final part size set to: {}".format(self.__final_part_size))
        except Exception as e:
            logger.exception("Failed to calculate chunks: {}".format(e))

    def __set_file_size(self):
        try:
            logger.debug("Setting file size")
            if self.file_size is not None:
                return

            # ftp connection
            ftp = FTP(self.__server)
            ftp.connect(self.__server, self.__port)
            ftp.login(self.__user_id, self.__password)

            # change working directory
            if self.__working_dir is not None:
                logger.debug("Changing working directory to : {}".format(self.__working_dir))
                ftp.cwd(self.__working_dir)

            if self.file_name is None or len(self.file_name) == 0:
                file_list = ftp.nlst()
                for file_name in file_list:
                    if str(file_name).endswith(".zip") or str(file_name).endswith(".dmg"):
                        self.file_name = file_name
                        break
            # binary mode
            logger.debug("Changing to binary mode")
            ftp.sendcmd("TYPE i")

            # file_size
            self.file_size = ftp.size(self.file_name)
            logger.debug("File size received from FTP server: {}".format(self.file_size))

            # back to ASCII mode
            logger.debug("Changing to ASCII mode")
            ftp.sendcmd("TYPE A")
            ftp.quit()
        except Exception as e:
            logger.exception("Failed to set file size: {}".format(e))
            raise SystemExit

    def __set_output_path(self):
        try:
            self.output_file_path = os.path.join(self.output_directory, self.file_name)
            if os.path.exists(self.output_file_path):
                os.remove(self.output_file_path)
        except Exception as e:
            logger.exception("Failed to set output path: {}".format(e))
            raise SystemExit

    def download(self):
        try:
            logger.info("Downloading File: {}".format(self.file_name))

            logger.info("Output Location: {}".format(self.output_file_path))

            self.__retrieve_parts()
            self.__combine_parts()
            shutil.rmtree(self.__download_directory)
            # Utils.delete_folder(self.__download_directory)

            """
            if self.md5 is not None:
                local_md5 = Utils.get_md5(self.output_file_path)
                if str(local_md5).lower() == str(self.md5).lower():
                    logger.info("MD5 successfully verified")
                    logger.info("File successfully downloaded: {}".format(self.output_file_path))
                    return True
                else:
                    logger.critical("MD5 do not match")
                    return False
            else:
                logger.info("File downloaded to: {}".format(self.output_file_path))
                logger.info("Please match MD5 to verify successful download")
                return None
            """
        except Exception as e:
            logger.exception("Failed to download file: {}".format(e))
            raise SystemExit

    def __retrieve_parts(self):
        try:
            retrievers_list = list()
            offset = 0
            if self.file_size is None:
                logger.critical("File size is None")
                return

            if self.__part_size is None or self.__final_part_size is None:
                logger.critical("Size of parts is None: {} - {}".format(self.__part_size, self.__final_part_size))
                return
            for i in range(NUM_PARTS):
                if i == (NUM_PARTS - 1):
                    current_part_size = self.__final_part_size
                else:
                    current_part_size = self.__part_size

                retriever = Retriever(self.__server_specs, i, current_part_size, offset, self.file_name, self.__download_directory, self.file_size)
                offset = offset + current_part_size
                retrievers_list.append(retriever)
                self.__parts_list.append(retriever.part_path)

            for retriever in retrievers_list:
                retriever.thread.join()

            current_size = 0
            for part in os.listdir(self.__download_directory):
                current_size += os.path.getsize(os.path.join(self.__download_directory, part))
            Retriever.progress_bar(current_size, self.file_size)
            logger.info("\n\n")

        except Exception as e:
            logger.exception("Failed to retrieve parts: {}".format(e))
            raise SystemExit

    def __combine_parts(self):
        try:
            for part in self.__parts_list:
                with open(self.output_file_path, "a+b") as fh, open(part, "r+b") as fh2:
                    fh.write(fh2.read())

        except Exception as e:
            logger.exception("Failed to combine parts: {}".format(e))
            raise SystemExit


class Retriever:

    thread_number = 0

    def __init__(self, server_specs, part_number, part_size, offset, file_name, output_directory, file_size):

        self.file_size = file_size
        self.__part_size = part_size
        self.__offset = offset
        self.__file_name = file_name

        self.__output_directory = output_directory
        self.part_path = os.path.join(output_directory, "part{}".format(part_number))
        self.__ftp = None
        self.__ftp_connection(server_specs)
        self.thread = threading.Thread(target=self.__retrieve)
        self.thread.start()
        Retriever.thread_number += 1
        self.thread_number = Retriever.thread_number

    def __ftp_connection(self, server_specs):
        """
        Setup FTP connection
        :param server_specs: dict()   --> Server, Port, UserID, Password
        :return:
        """
        try:
            self.__ftp = FTP(server_specs["Server"])
            self.__ftp.connect(server_specs["Server"], server_specs["Port"])
            self.__ftp.login(server_specs["UserId"], server_specs["Password"])
            wd = server_specs["WorkingDirectory"]
            if wd is not None:
                self.__ftp.cwd(wd)

        except Exception as e:
            logger.exception("Failed to establish ftp connection: {}".format(e))
            sys.exit()

    def __retrieve(self):
        """
        Retrieve individual parts
        :return:
        """
        try:
            if self.__ftp is None:
                logger.critical("FTP connection is not established")
                return False
            else:
                self.__ftp.retrbinary("RETR " + self.__file_name, self.__call_back_function, blocksize=BLOCK_SIZE, rest=self.__offset)
        except Exception as e:
            logger.exception("Failed to retrieve part: {}".format(e))
            sys.exit()

    def __call_back_function(self, block_size):
        try:
            with open(self.part_path, "a+b") as fh:
                fh.write(block_size)
            current_size = os.path.getsize(self.part_path)
            if current_size >= self.__part_size:
                with open(self.part_path, "r+b") as fh:
                    fh.truncate(self.__part_size)
                sys.exit()

            size = 0
            for part in os.listdir(self.__output_directory):
                size += os.path.getsize(os.path.join(self.__output_directory, part))

            target = self.file_size
            Retriever.progress_bar(size, target)

        except Exception as e:
            logger.exception("Failed to write part: {} - {}".format(self.part_path, e))
            sys.exit()

    # TODO : cleaner progress bar
    @staticmethod
    def progress_bar(current_value, target_value):
        """
        Purpose : prints progress bar based on proportion of current_value with final_value
        :param current_value: current value of iterating item
        :param target_value: target_value of iterating item
        :return: None
        """
        try:
            progress_length = 40
            progress_string = "#"
            remaining_string = "-"

            percent = float(current_value) * 100 / target_value
            percent = round(percent, 2)

            num_progress = int(progress_length * (float(current_value) / target_value))
            num_remaining = progress_length - num_progress

            progress = num_progress * progress_string
            remaining = num_remaining * remaining_string

            progress_format = "Progress : [" + "{0}{1}" + "]" + " : " + "{2}" + "% Complete "
            progress_message = progress_format.format(progress, remaining, str(percent))

            print("\r" + progress_message, end="")

        except Exception as e:
            logger.exception("Failed to print progress bar: {}".format(e))


class Zero(Cmd):

    def __init__(self):
        super().__init__()
        logger.info("Initiating application...")

        if os.name == "nt":
            logger.info("Type 'help' and hit 'Enter' to see list of commands and their basic usage\n")
        else:
            logger.info("Type 'help' and hit 'return' to see list of commands and their basic usage\n")

        self.server = ""
        self.user_id = ""
        self.password = ""
        self.port = 21

        self.set_server()
        self.set_login_credentials()
        self.server_specs = dict({})

    def set_server_specs(self):
        """
        Sets server specs
        :return:
        """
        try:
            logger.debug("Setting server specs")
            self.server_specs["Server"] = self.server
            self.server_specs["UserId"] = self.user_id
            self.server_specs["Password"] = self.password
            self.server_specs["Port"] = self.port
        except Exception as e:
            logger.error("Failed to set server specs: {}".format(e))

    def attempt_login(self):
        """Check login creds"""
        try:
            logger.info("Validating credentials...")
            self.ftp = FTP(self.server)
            self.ftp.set_pasv(True)
            self.ftp.connect(self.server, self.port, timeout=100)
            self.ftp.login(self.user_id, self.password)
            return True

        except Exception as e:
            logger.error("Failed to login: {}".format(e))
            return False

    def do_d(self, args):
        """Downloads the build based from the entered ftp-directory"""
        self.do_download(args)

    def do_download(self, args):
        """Downloads the build based from the entered ftp-directory"""
        self.set_server_specs()
        wd = None
        try:
            wd = self.cwd_routine()
            if wd is False or wd is None:
                raise SystemExit
        except:
            pass

        self.server_specs["WorkingDirectory"] = wd

        logger.debug("Server specs set")

        for k, v in self.server_specs.items():
            logger.debug("{} : {}".format(k, v))

        file_name = ""
        desktop_path = Utils.get_desktop_path()

        output_file_dir = os.path.join(desktop_path, "Downloads")
        logger.info("Downloading application")
        download = Download(self.server_specs, file_name, output_file_dir)
        download.download()

    def cwd_routine(self):
        try:
            count = 0
            limit = 3
            while count < limit:
                try:
                    logger.debug("Setting FTP directory")
                    wd = str(input("Enter FTP directory: ")).strip()
                    logger.debug("FTP working directory: {}".format(wd))

                    count = count + 1
                    self.ftp.cwd(wd)
                    logger.info("FTP directory correctly set")
                    return wd
                except Exception as e:
                    logger.error("Failed to change working directory.: {}".format(e))

                logger.info("Available attempts: {}\n".format(limit - count))
            logger.error("Please check the directory and try again or please contact admin")
            return False
        except Exception as e:
            logger.error("Failed to change directory: {}".format(e))

    def set_login_credentials(self):
        try:
            logger.debug("Setting login credentials")

            logger.debug("Password entered")
            logger.info("\n")
            if self.server is not None and len(self.server) > 0:
                count = 0
                limit = 3
                while count < limit:
                    count = count + 1

                    self.user_id = str(input("Enter user-id: ")).lower()
                    logger.debug("User-id entered: {}".format(self.user_id))

                    if not self.user_id.endswith("@{}".format(DOMAIN)):
                        self.user_id += "@{}".format(DOMAIN)

                    self.password = str(getpass.getpass("Enter password: ")).strip()

                    status = self.attempt_login()
                    if not status:
                        logger.info("Available attempts: {}\n".format(limit - count))
                    else:
                        logger.info("Login successful")
                        return
                logger.info("Crossed limits of login-attempts. Exiting application")
                raise SystemExit

        except Exception as e:
            logger.error("Failed to set login credentials: {}".format(e))
            raise SystemExit

    def set_server(self):
        try:
            logger.debug("Setting server")

            self.server = str(input("Enter server: sjstore(s) / indstore(i): ")).lower()

            logger.debug("Server entered by user: {}".format(self.server))

            if self.server.startswith(SERVER_NAME) or self.server == SERVER_NAME.lower()[0]:
                self.server = FULL_SERVER_NAME

            logger.info("Server set: {}".format(self.server))

            if self.user_id is not None and self.password is not None and len(self.user_id) > 0 and len(self.password) > 0:
                self.attempt_login()
        except Exception as e:
            logger.error("Failed to set server: {}".format(e))

    def do_clc(self, args):
        """Change Login Credentials"""
        self.do_change_login_creds(args)

    def do_change_login_creds(self, args):
        """Change Login Credentials"""
        self.set_login_credentials()

    def do_ss(self, args):
        """Change Server (sjstore / indstore)"""
        self.do_set_server(args)

    def do_set_server(self, args):
        """Change Server (sjstore / indstore)"""
        self.set_server()

    def do_e(self, args):
        """Exits Zero - Use e / exit to exit Zero"""
        self.do_exit(args)

    @staticmethod
    def do_exit(args):
        """Exits Zero - Use e / exit to exit Zero"""
        try:
            logger.info("Exiting Zero...")
            raise SystemExit
        except Exception as e:
            logger.error("Failed to exit Zero. Please exit manually")
            logger.exception(str(e))

    def do_v(self, args):
        """Version Number || Build Number"""
        self.do_version(args)

    def do_version(self, args):
        """Version Number || Build Number"""
        logger.info("Zero v{0} - {1}".format(VERSION, TIMESTAMP))
        logger.info("To talk about Zero, contact {}".format(AUTHOR))

    def emptyline(self):
        pass


if __name__ == '__main__':
    prompt = Zero()
    prompt.prompt = '> '
    message = "\nStarting prompt..."
    prompt.cmdloop(message)