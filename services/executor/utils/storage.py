import os
import shutil
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


def create_tree(file_path):
    os.makedirs(file_path.rsplit("/",1)[0], exist_ok=True)


# use this method to avoid Invalid cross-device link error
# https://stackoverflow.com/questions/42392600/oserror-errno-18-invalid-cross-device-link
# shutil.move() seems to not detect the different filesystem
def move(old_file, new_file):
    shutil.copy(old_file, new_file)
    os.remove(old_file)


class Storage:
    def __init__(self, storage_path=None):
        if storage_path:
            self.path = Path(storage_path)
        elif os.getenv('STORAGE'):
            self.path = Path(os.getenv('STORAGE'))
        else:
            ROOT_DIR_PROJECT = ROOT_DIR.parent.parent
            self.path = ROOT_DIR_PROJECT.joinpath("storage")

    def abs_path(self, r_path):
        return str(self.path.joinpath(r_path))

    def move_to(self, l_file, s_file):
        s_abs_file = self.abs_path(s_file)
        create_tree(s_abs_file)
        move(l_file, s_abs_file)

    def copy_from(self, s_file, l_file):
        s_abs_file = self.abs_path(s_file)
        create_tree(l_file)
        shutil.copy(s_abs_file, l_file)

    def remove(self, s_file):
        os.remove(self.abs_path(s_file))

    def remove_tree(self, s_dir):
        shutil.rmtree(self.abs_path(s_dir))
