from pdf2image import convert_from_path
import cv2
import tempfile
from pathlib import Path
from PIL import Image
import os
import shutil

TEMP_FOLDER = Path(__file__).resolve().parent.joinpath('temp')

class PreviewHandler:
    RED = (0, 6, 225)
    GREEN = (0, 154, 23)

    def createDocumentPreview(self, pdf_file_path, output_f, results):
        
        if not os.path.exists(TEMP_FOLDER):
            os.makedirs(TEMP_FOLDER)

        filename = Path(pdf_file_path).name[:-4]
        print(filename)
        convert_from_path(
            pdf_file_path,
            500,
            single_file=True,
            output_file=filename,
            fmt="png",
            output_folder=TEMP_FOLDER,
        )

        print(str(TEMP_FOLDER.joinpath(f"{filename}.png")))

        img = cv2.imread(str(TEMP_FOLDER.joinpath(f"{filename}.png")))

        h, w, c = img.shape

        offset = 0

        font = cv2.FONT_HERSHEY_COMPLEX

        print(max(results, key=lambda x: len(x[0])))

        x = int(w - cv2.getTextSize(max(results, key=lambda x: len(x[0]))[0], font, 2, 5)[0][0])
        y = int(cv2.getTextSize(results[0][0], font, 2, 5)[0][1])
        padding = 20

        for result, status in results:
            offset += y + padding
            test = cv2.putText(
                img,
                result,
                (x, offset),
                font,
                2,
                self.GREEN if status else self.RED,
                5,
            )

        cv2.imwrite(str(output_f.joinpath(f"{filename}.png")), img)
        print(f'filname : {filename}')
        print(f'output path : {output_f}')
        shutil.rmtree(str(TEMP_FOLDER))
        return str(output_f.joinpath(f"{filename}.png"))

    def createSummary(self, folder, output_pdf_filename):
        images = [Image.open(Path(folder).joinpath(f)) for f in os.listdir(folder)]

        images[0].save(
            output_pdf_filename,
            "PDF",
            resolution=100.0,
            save_all=True,
            append_images=images[1:],
        )
