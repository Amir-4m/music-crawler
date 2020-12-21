import os
import linecache
import sys
import logging
from urllib.parse import unquote

from pid import PidFile

logger = logging.getLogger(__file__)


class UploadTo:
    """
    This class handle the path of each file that download.
    """
    def __init__(self, field_name):
        self.field_name = field_name

    def __call__(self, instance, filename):
        path = self.path_creator(instance) or f'{filename}'
        return path.replace(' ', '')

    def path_creator(self, instance):
        """
        thumbnail example url: https://nicmusic.net/wp-content/uploads/***.jpg
        music example url: http://dl.nicmusic.net/nicmusic/024/093/***.mp3
        :param instance: CMusic object.
        :return: Created path from URL of site.
        """
        value = unquote(getattr(instance, f'link_{self.field_name}', ''))
        if value.find('/nicmusic/') != -1:
            return f"{value[value.index('/nicmusic/') + 10:]}"
        elif value.find('/wp-content/') != -1:
            return f"{value[value.index('/wp-content/'):]}"
        elif value.find('/Ganja2Music/') != -1:
            return f"{value[value.index('/Ganja2Music/') + 13:]}"
        elif value.find('/Image/') != -1:
            return f"{value[value.index('Image/'):]}"

    def generate_name(self, filename):
        base_filename, file_extension = os.path.splitext(filename)
        return base_filename, file_extension

    def deconstruct(self):
        return 'apps.musicfa.utils.UploadTo', [self.field_name], {}


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    logger.error('>> EXCEPTION IN ({}, LINE {} "{}"):\n {}'.format(filename, lineno, line.strip(), exc_obj))


def per_num_to_eng(number):
    intab = '۱۲۳۴۵۶۷۸۹۰١٢٣٤٥٦٧٨٩٠'
    outtab = '12345678901234567890'
    translation_table = str.maketrans(intab, outtab)
    return number.translate(translation_table)


def check_running(function_name):
    if not os.path.exists('./locks'):
        os.mkdir('./locks')
    file_lock = PidFile(str(function_name), piddir='./locks')
    try:
        file_lock.create()
        return file_lock
    except:
        return None


def close_running(file_lock):
    file_lock.close()


