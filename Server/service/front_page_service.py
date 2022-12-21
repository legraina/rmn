import fitz
import traceback
import unidecode
import os
import subprocess

from colorama import Fore, Style
from pathlib import Path


class FrontPageHandler:
    CMD = "pdflatex"
    INPUT_CONTENT = "\\renewcommand{\\nom}{%s}\n\\renewcommand{\\matricule}{%s}\n"

    def addFrontPages(
        self, work_directory, input_folder, suffix, latex_front_page, latex_input_file
    ):
        folders = os.listdir(input_folder)
        for folder in folders:
            folder_path = os.path.join(input_folder, folder)
            if os.path.isfile(folder_path):
                continue

            files = os.listdir(folder_path)
            if len(files) != 1:
                raise ValueError(
                    "Subfolder %s does not contain only one file, but %d files"
                    % (folder, len(files))
                )

            # pdf file
            file = files[0]
            file_path = os.path.join(folder_path, file)

            # rename it
            # use folder name: "Nom complet_Identifiant_Matricule_assignsubmission_file_"
            fullname, _id, matricule, _a, _f, _ = folder.split("_")
            tempname = "_".join(fullname.split(" "))
            name = os.path.join(
                folder_path,
                f"{tempname}_{str(matricule)}{f'_{suffix}.pdf' if suffix else file}",
            )

            self.copy_file_with_front_page(
                file_path,
                latex_front_page,
                latex_input_file,
                work_directory,
                name,
                name=fullname,
                mat=matricule,
            )

    def copy_file_with_front_page(
        self,
        file,
        latex_front_page,
        latex_input_file,
        work_directory,
        output_filename,
        name=None,
        mat=None,
    ):
        # add front page if any
        f = file.rsplit("/")[-1]
        f_page = None
        try:
            f_page = self.create_front_page(
                latex_front_page, latex_input_file, name, mat, work_directory
            )
            doc = fitz.Document(f_page)
            copy = fitz.Document(file)
            doc.insert_pdf(copy)
            doc.save(file, garbage=4, deflate=True)
            os.rename(file, output_filename)
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)
            print(
                Fore.RED + "Error when creating new pdf for %s" % file + Style.RESET_ALL
            )
            return False
        return True

    def create_front_page(
        self,
        latex_file,
        latex_input_file,
        name,
        matricule,
        tmp_dir,
    ):
        # remove ascents
        no_accent_name = unidecode.unidecode(name)
        # write the input file
        input_data = self.INPUT_CONTENT % (no_accent_name, matricule)

        with open(latex_input_file, "w") as f:
            f.write(input_data)

        current_dir = os.path.dirname(__file__)
        os.chdir(tmp_dir)

        # compile latex file
        try:
            subprocess.check_call([self.CMD, latex_file], timeout=1)
        except subprocess.TimeoutExpired:
            raise ChildProcessError("Subprocess latex time out after 1 second.")

        os.chdir(current_dir)

        # return path to pdf
        fname = os.path.basename(latex_file)
        fpdf = fname.rsplit(".", 1)[0] + ".pdf"
        return os.path.join(tmp_dir, fpdf)
