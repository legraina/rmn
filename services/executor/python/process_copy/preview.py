from pdf2image import convert_from_path
import cv2
from pathlib import Path
from PIL import Image
import os
import shutil


TEMP_FOLDER = Path(__file__).resolve().parent.joinpath('temp')


class PreviewHandler:
    RED = (0, 6, 225)
    GREEN = (0, 154, 23)
    BLUE = (225, 105, 65)
    ORANGE = (30, 144, 255)

    def createDocumentPreview(self, pdf_file_path, output_f, results, dpi=300, box=None, boxes=[], mat_box=None):
        if not os.path.exists(TEMP_FOLDER):
            os.makedirs(TEMP_FOLDER)

        filename = Path(pdf_file_path).name[:-4]
        print(filename)
        convert_from_path(
            pdf_file_path,
            dpi=dpi,
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

        # grade box
        if box:
            x0 = int(box[0] * img.shape[1])
            x1 = int(box[1] * img.shape[1])
            y0 = int(box[2] * img.shape[0])
            y1 = int(box[3] * img.shape[0])
            cv2.rectangle(img, (x0, y0), (x1, y1), self.BLUE, 10)
            for c in boxes:
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(img, (x0 + x, y0 + y), (x0 + x + w, y0 + y + h), self.ORANGE, 5)

        # mat box
        if mat_box:
            x0 = int(mat_box[0] * img.shape[1])
            x1 = int(mat_box[1] * img.shape[1])
            y0 = int(mat_box[2] * img.shape[0])
            y1 = int(mat_box[3] * img.shape[0])
            cv2.rectangle(img, (x0, y0), (x1, y1), self.BLUE, 10)

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
