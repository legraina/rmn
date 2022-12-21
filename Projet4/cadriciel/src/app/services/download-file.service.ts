import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class DownloadFileService {

  constructor(private http: HttpClient) { }

  download(url: string, jobId: string, fileType: string): Blob {
    const formdata: FormData = new FormData();
    formdata.append('job_id', jobId);
    formdata.append('file', fileType);

    let file: Blob;

    this.http.post(url, formdata, {responseType: 'blob'}).subscribe(
    (data) => {
      file = data;
    },
    (error) => {
      console.error(error);
    });
    return file;
  }
}
