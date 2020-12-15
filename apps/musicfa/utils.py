import os
import linecache
import sys
import logging
from urllib.parse import unquote

logger = logging.getLogger(__file__)


class UploadTo:
    """
    This class handle the path of each file that download.
    """
    def __init__(self, field_name):
        self.field_name = field_name

    def __call__(self, instance, filename):
        return f'{self.field_name}{self.path_creator(instance)}'

    def path_creator(self, instance):
        """
        thumbnail example url: https://nicmusic.net/wp-content/uploads/2020/12/Saeed-Azar-Dore-Tekrari-500x500.jpg
        music example url: http://dl.nicmusic.net/nicmusic/024/093/Saeed Azar - Dore Tekrari.mp3
        :param instance: CMusic object.
        :return: Created path from URL of site.
        """
        value = unquote(getattr(instance, f'link_{self.field_name}', ''))
        if value.find('/nicmusic/') != -1:
            return f"/{value[value.index('/nicmusic/') + 10:]}"
        elif value.find('/wp-content/') != -1:
            return f"/{value[value.index('/wp-content/'):]}"

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
