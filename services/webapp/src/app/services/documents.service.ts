import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { UserService } from './user.service';
import { SERVER_URL } from '../utils';

@Injectable({
  providedIn: 'root'
})
export class DocumentsService {

  jobId: string;
  documentsList: Array<any>;
  subgroupsList: Array<string>;

  constructor(private http: HttpClient,
              private userService: UserService) { }

  async getDocuments(jobId: string) {
    const formdata: FormData = new FormData();
    formdata.append('job_id', jobId);
    this.userService.addTokens(formdata);
    this.subgroupsList = [""];

    try {
      const promise = await this.http.post<any>(`${SERVER_URL}documents`, formdata).toPromise();
      this.documentsList = promise['response'];
      // fetch subgroups if any
      this.documentsList.forEach((exam: any) => {
        if (exam.group && !this.subgroupsList.includes(exam.group)) {
            this.subgroupsList.push(exam.group);
        }
      });
      this.subgroupsList.sort((a, b) => {
        if (a === "") return -1;
        return a.localeCompare(b);
      });
    } catch (error) {
      console.log(error);
    }
  }

}
