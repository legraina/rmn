import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { UserService } from './user.service';
import { SERVER_URL } from '../utils';

@Injectable({
  providedIn: 'root'
})
export class ValidationService {

  constructor(
    private router: Router,
    private http: HttpClient,
    private userService: UserService
  ) { }

  async validateDocument(jobId, validatingCopy, predictions, registration, total, status) {
    const formdata: FormData = new FormData();
    formdata.append('token', this.userService.token);
    formdata.append('job_id', jobId);
    formdata.append('document_index', validatingCopy.toString());
    formdata.append('subquestion_predictions', JSON.stringify(predictions));
    formdata.append('matricule', registration);
    formdata.append('total', total);
    formdata.append('status', status);

    let response;
    try {
      const promise = await this.http.post<any>(`${SERVER_URL}documents/update`, formdata).toPromise();
      response = promise['response'];
    } catch (error) {
      console.log(error);
    }
    return response;
  }


  async validateJob(jobId, moodle_ind) {
    const formdata: FormData = new FormData();
    formdata.append('job_id', jobId);
    formdata.append('user_id', this.userService.currentUsername);
    formdata.append('token', this.userService.token);
    formdata.append('moodle_ind', (Number(moodle_ind)).toString());
    let response;
    try {
      const promise = await this.http.post<any>(`${SERVER_URL}job/validate`, formdata).toPromise();
      response = promise['response'];

    } catch (error) {
      console.log(error);
    }
    return response;
  }
}
