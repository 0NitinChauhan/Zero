import os
import shutil
import hashlib
import getpass
from src.LogLib import LogLib

logger = LogLib.get_logger()


class Utils:

    def __init__(self):
        pass

    @staticmethod
    def delete_folder(folder_path):
        try:
            shutil.rmtree(folder_path)
            if os.path.exists(folder_path):
                logger.debug("Failed to delete directory: {0}".format(folder_path))
                return False
            else:
                logger.debug("Directory successfully deleted: {0}".format(folder_path))
                return True
        except Exception as e:
            logger.error(str(e), exc_info=True)
            return False

    @staticmethod
    def get_md5(file_path):
        try:
            m = hashlib.md5()
            with open(file_path, "rb") as f:
                data = f.read()  # read file in chunk and call update on each chunk if file is large.
                m.update(data)

                md5 = m.hexdigest()
                logger.info("Returning MD5".format(md5))
                return md5
        except Exception as e:
            logger.exception(str(e))
            return None

    @staticmethod
    def get_current_user():
        """
        () --> str
        Purpose : Returns current user
        """
        try:
            logger.debug("get_current_user() called")
            if os.name == "nt":
                username = getpass.getuser()
            else:
                username = os.getlogin()
            logger.debug("Returning current user - " + username)
            return username
        except Exception as e:
            logger.exception(str(e))
            return None

    @staticmethod
    def get_desktop_path():
        """ () --> str
        Purpose : returns desktop path for current user
        :return: desktop_path
        """
        if os.name == "nt":
            root_path = os.path.join("C:\\Users", Utils.get_current_user())
        elif os.name == "posix":
            root_path = os.path.join("/Users", Utils.get_current_user())

        for subdir in os.listdir(root_path):
            try:
                if subdir.lower() == "desktop":
                    desktop_path = os.path.join(root_path, subdir)
                    logger.debug("returned desktop path - " + desktop_path)
                    return desktop_path
            except Exception as e:
                logger.debug(str(e))
                continue
        return None
