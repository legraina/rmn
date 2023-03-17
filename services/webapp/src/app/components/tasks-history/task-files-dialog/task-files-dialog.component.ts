import { Component, OnInit, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NotificationService } from 'src/app/services/notification.service';
import { UserService } from 'src/app/services/user.service';
import { saveAs } from 'file-saver';
import { HttpClient, HttpEventType } from '@angular/common/http';
import { SERVER_URL } from 'src/app/utils';

export interface DialogData {
  taskId: string;
  nbZipFile: number;
}

@Component({
  selector: 'app-task-files-dialog',
  templateUrl: './task-files-dialog.component.html',
  styleUrls: ['./task-files-dialog.component.css']
})
export class TaskFilesDialogComponent implements OnInit {

  downloading: boolean = false;
  downloadProgress = 0
  constructor(
    public dialogRef: MatDialogRef<TaskFilesDialogComponent>,
    private notifyService : NotificationService,
    private userService: UserService,
    private http: HttpClient,
    @Inject(MAT_DIALOG_DATA) public data: DialogData
  ) { }

  ngOnInit(): void {
  }

  showNotificationError(){
    this.notifyService.showError("Assurez-vous de remplir le champ du nom de fichier!", "ERREUR")
  }

  numSequence(n: number): Array<number> {
    return Array(n);
  }

  setZipIds(index : number) : string{
    let value : string = "zip_file-index-" + index.toString();
    return value;
  }

  setDefaultZipValues(index : number) : string{
    let value : string;
    if (index == 0) {
      value = "copies";
    } else {
      value = "moodle-" + index.toString();
    }
    return value;
  }

  checkInputBox(inputId : string, index : number){
    let inputValue : string;

    if(inputId === 'zip_file'){
      inputId = this.setZipIds(index);
      inputValue = (<HTMLInputElement>document.getElementById(inputId)).value;
      inputId = inputId.split('-index-')[0];
    }else{
      inputValue = (<HTMLInputElement>document.getElementById(inputId)).value;
    }

    if(inputValue.trim() === ""){
      this.showNotificationError();
    }else{
      this.downloadFile(`${SERVER_URL}file/download`, inputValue, inputId, index);
    }
  }

  downloadFile(requestURL : string, filename : string, fileType: string, index : number){
    const formdata: FormData = new FormData();
    formdata.append('token', this.userService.token);
    formdata.append('job_id', this.data.taskId);
    formdata.append('file', fileType);
    formdata.append('zip_index', index.toString());
    if ( !this.downloading) {
      this.downloading = true;
      // this.notifyService.showInfo('Téléchargement...', "")
      this.http.post(requestURL, formdata, {responseType: 'blob', reportProgress: true, observe: "events"}).subscribe(
        (data) => {
          if (data.type == HttpEventType.DownloadProgress) {
            this.downloadProgress = data.total ? Math.round(100 * data.loaded / data.total) : 0
          } else if (data.type == HttpEventType.Response) {
            let typeExport = 'text/csv'
            if (fileType == 'zip_file') {
              typeExport = 'application/zip'
            }
            const file = new Blob([data.body as any], { type: typeExport });
            let downloadURL = window.URL.createObjectURL(file);
            saveAs(downloadURL, filename);

            this.downloading = false;
            this.downloadProgress = 0;
          }
        },
        (error) => {
          console.error(error);
          this.downloading = false;
          this.downloadProgress = 0;
        });
    } else {
      this.notifyService.showWarning("Un fichier est en cours de téléchargement!", "Attention" )
    }


  }

  cancel(): void {
    this.dialogRef.close('');
  }
}
