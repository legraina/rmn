import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import * as saveAs from 'file-saver';
import { NotificationService } from 'src/app/services/notification.service';
import { TasksService } from 'src/app/services/tasks.service';
import { UserService } from 'src/app/services/user.service';
import { SERVER_URL } from 'src/app/utils';

@Component({
  selector: 'app-presentation-page',
  templateUrl: './presentation-page.component.html',
  styleUrls: ['./presentation-page.component.css']
})
export class PresentationPageComponent implements OnInit {
  copies: File;
  latexFrontPage: File;
  latexInputPage: File;

  copiesName: string = "";
  latexFrontPageName: string = "";

  suffix: string = "";

  disabled: boolean = false;


  constructor(private router: Router, private notifyService: NotificationService, private http: HttpClient, private userService: UserService) { }

  ngOnInit(): void {
  }

  CopiesFileEvent(fileInput: Event) {
    let target = fileInput.target as HTMLInputElement;
    let file: File = (target.files as FileList)[0];
    this.copiesName = file.name;
    this.copies = file;
  }

  latexFrontPageEvent(fileInput: Event) {
    let target = fileInput.target as HTMLInputElement;
    let file: File = (target.files as FileList)[0];
    this.latexFrontPageName = file.name;
    this.latexFrontPage = file;
  }


  updateSuffix(event: KeyboardEvent) {
    let regex = new RegExp("^[a-zA-ZÀ-ÿ0-9\-\_\ ]+$");
    let key = String.fromCharCode(!event.charCode ? event.which : event.charCode);
    if (!regex.test(key)) {
      event.preventDefault();
    }
  }

  checkDisabled() {
    if (this.copiesName !== "" && this.latexFrontPageName !== "" ) {
      return false;
    } else {
      return true;
    }
  }

  cancel() {
    this.copiesName = "";
    this.latexFrontPageName = "";
    this.suffix = "";
    this.router.navigate(['/main-menu']);
  }

  createPresentation() {
    if (this.checkDisabled()) {
      this.notifyService.showError("Assurez-vous de complêter toutes les étapes!", "ERREUR")
    } else {
      this.disabled = true;

      // post request
      const formdata: FormData = new FormData();
      formdata.append('user_id', this.userService.currentUsername);
      formdata.append('token', this.userService.token);
      formdata.append('suffix', this.suffix);
      formdata.append('moodle_zip', this.copies);
      formdata.append('latex_front_page', this.latexFrontPage);

      let file: Blob;

      this.http.post(`${SERVER_URL}front_page`, formdata, { responseType: 'blob' }).subscribe(
        (data) => {
          // moodle.zip in data
          file = data;
          let downloadURL = window.URL.createObjectURL(data);
          saveAs(downloadURL, this.copiesName);
          this.disabled = false;
        },
        (error) => {
          this.notifyService.showError(error.message, "ERREUR")
          this.disabled = false;
        });

    }
  }

  reroute() {
    this.router.navigate(['/main-menu']);
  }


}
