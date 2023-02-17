import os
import shutil
import glob
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


def create_tree(file_path):
    os.makedirs(file_path.rsplit("/",1)[0], exist_ok=True)


class Storage:
    def __init__(self, storage_path = None):
        if storage_path:
            self.path = Path(storage_path)
        elif os.getenv('STORAGE'):
            self.path = Path(os.getenv('STORAGE'))
        else:
            self.path = ROOT_DIR.joinpath("storage")
        print("Access:", os.access(self.path, os.R_OK))
        print("Access:", os.access(self.path, os.W_OK))

    def abs_path(self, r_path):
        return str(self.path.joinpath(r_path))

    def move_to(self, l_file, s_file):
        s_abs_file = self.abs_path(s_file)
        create_tree(s_abs_file)
        shutil.move(l_file, s_abs_file)

    def copy_from(self, s_file, l_file):
        s_abs_file = self.abs_path(s_file)
        create_tree(l_file)
        shutil.copy(s_abs_file, l_file)

    def remove(self, s_file):
        abs_path = self.abs_path(s_file)
        for f in glob.glob(str(abs_path)):
            os.remove(f)

    def remove_tree(self, s_dir):
        shutil.rmtree(self.abs_path(s_dir))
