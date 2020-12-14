import os


class UploadTo:
    def __init__(self, filed_name):
        self.filed_name = filed_name

    def __call__(self, instance, filename):
        base_filename, file_extension = self.generate_name(filename)
        return f'musics/{self.filed_name}/{base_filename}{file_extension}'

    def generate_name(self, filename):
        base_filename, file_extension = os.path.splitext(filename)
        return base_filename, file_extension

    def deconstruct(self):
        return 'apps.musicfa.utils.UploadTo', [self.filed_name], {}
