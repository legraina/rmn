import { Component, OnInit, Inject } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NotificationService } from "../../../services/notification.service";
import { UserService } from "../../../services/user.service";
import { HttpClient } from '@angular/common/http';
import { SERVER_URL } from 'src/app/utils';

export interface DialogData {
  taskId: string;
  taskName: string;
}
@Component({
  selector: 'app-task-share-dialog',
  templateUrl: './task-share-dialog.component.html',
  styleUrls: ['./task-share-dialog.component.css']
})
export class TaskShareDialogComponent implements OnInit {

  url: string;
  constructor(
    public dialogRef: MatDialogRef<TaskShareDialogComponent>,
    private notifyService : NotificationService,
    private userService: UserService,
    private http: HttpClient,
    @Inject(MAT_DIALOG_DATA) public data: DialogData) {}

  ngOnInit(): void {
    const formdata: FormData = new FormData();
    formdata.append('token', this.userService.token);
    formdata.append('job_id', this.data.taskId);
    this.http.post<any>(`${SERVER_URL}job/share`, formdata).subscribe(
      (data) => {
        let resp = data['response'];
        if (resp.share_url) {
          this.url = resp.share_url;
        } else {
          this.close(false);
        }
      });
  }

  unshare(): void {
    const formdata: FormData = new FormData();
    formdata.append('token', this.userService.token);
    formdata.append('job_id', this.data.taskId);
    this.http.post<any>(`${SERVER_URL}job/unshare`, formdata).subscribe(
      (data) => {
        this.close(data['response'] == "OK");
      });
  }

  close(r: any): void {
    this.dialogRef.close(r);
  }

  selectText(event): void {
    // const input = document.getElementById('text-box');
    // input.focus();
    event.target.select();
  }

}
