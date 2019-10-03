import os
import pathlib
import inspect
import datetime
import logging


class LogLib:

    logger = None

    def __init__(self):
        pass

    @staticmethod
    def __define_today():
        year = datetime.date.today().strftime("%Y")
        month = datetime.date.today().strftime("%B")
        day = datetime.date.today().strftime("%d")
        year = year[-2:]
        if month != "June" or month != "July":
            month = month[:3]
        return [day, month, year]

    @staticmethod
    def __get_log_package():
        current_file = inspect.getfile(inspect.currentframe())
        root_path = str(pathlib.Path(current_file).parent.parent)
        log_package = os.path.join(root_path, "logs")
        return log_package

    @staticmethod
    def __get_log_environ():

        folder = "-".join(LogLib.__define_today())

        log_package = LogLib.__get_log_package()

        log_folder = os.path.join(log_package, folder)

        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        log_file = "-".join([datetime.datetime.now().strftime("%H"), datetime.datetime.now().strftime("%M"), "logs"])
        log_file = log_file + ".log"

        log_file = os.path.join(log_folder, log_file)

        log_format = "%(levelname)s :  %(asctime)s : [%(filename)s] : [%(funcName)s] : %(message)s"

        return log_file, log_format

    @staticmethod
    def get_logger():
        if LogLib.logger is None:
            log_environment = LogLib.__get_log_environ()

            logger = logging.getLogger(__name__)

            logger.setLevel(logging.DEBUG)
            file_handler = logging.FileHandler(log_environment[0])
            formatter = logging.Formatter(log_environment[1])

            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)

            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)

            logger.addHandler(file_handler)
            logger.addHandler(stream_handler)
            LogLib.logger = logger
        return LogLib.logger

    @staticmethod
    def delete_log_folder():
        today = LogLib.__define_today()
        day = today[0]
        month = today[1]
        year = today[2]

        monthly_dict = {"Jan": (1, 31), "Feb": (2, 28), "Mar": (3, 31), "Apr": (4, 30), "May": (5, 31), "June": (6, 30),
                        "July": (7, 31), "Aug": (8, 31),
                        "Sep": (9, 30), "Oct": (10, 31), "Nov": (11, 30), "Dec": (12, 31)}

        # date = [int(day), monthly_dict[month], int(year)]

        date = "{0}-{1}-{2}".format(day, month, year)
        date = date.split("-")
        date = [int(date[0]), int(monthly_dict[date[1]][0]), int(date[2])]
        log_package = LogLib.__get_log_package()
        for dir_name in os.listdir(log_package):
            parts = dir_name.split("-")
            parts = [int(parts[0]), int(monthly_dict[parts[1]][0]), int(parts[2])]
            print(parts, date)
            print(LogLib.count_days(parts, date))

    @staticmethod
    def count_days(first, second):

        monthly_dict = {1 : 31, 2 : 28, 3 : 31, 4 : 30, 5 : 31, 6 : 30, 7 : 31, 8 : 31, 9 : 30, 10 : 31, 11 : 30, 12 : 31}
        num_days = 0
        year_one = first[2]
        month_one = first[1]
        day_one = first[0]

        year_two = second[2]
        month_two = second[1]
        day_two = second[0]

        if year_two - year_one >= 2 or (year_two - year_one >= 1 and month_two - month_one > 0):
            num_days = num_days + (year_two - year_one)*365

        for i in range(month_one + 1, (12 + month_two) % 12):
            if i == 0:
                i = 12
            num_days = num_days + monthly_dict[i]

        if month_two == month_one:
            num_days = num_days + day_two - day_one
        else:
            num_days = num_days + monthly_dict[month_one] - day_one + day_two

        one = 2000 + year_one
        two = 2000 + year_two

        for i in range(one + 1, two):
            if LogLib.is_leap_year(i):
                num_days = num_days + 1

        if LogLib.is_leap_year(one):
            if month_one <= 2:
                num_days = num_days + 1

        if LogLib.is_leap_year(two):
            if month_two > 2:
                num_days = num_days + 1
        return num_days

    @staticmethod
    def is_leap_year(year):
        if year % 4 != 0:
            return False
        elif year % 100 != 0:
            return False
        elif year % 400 != 0:
            return False
        return True
