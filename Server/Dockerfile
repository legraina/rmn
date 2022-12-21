# syntax=docker/dockerfile:1

FROM python:3.9

ENV ENVIRONNEMENT=production 

ENV PYTHONUNBUFFERED=1

WORKDIR /Server

COPY . .

RUN apt-get update \
 && apt-get install -y sudo

RUN pip install -r requirements.txt

RUN pip uninstall -y PyCrypto
RUN pip install PyCryptodome

RUN pip uninstall -y PyMuPDF
RUN pip install PyMuPDF

RUN pip uninstall -y httplib2
RUN pip install httplib2==0.15.0

RUN sudo apt install -y texlive-latex-recommended
RUN sudo apt-get install -y texlive-lang-french

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]