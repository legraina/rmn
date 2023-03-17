import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CanActivate, CanActivateChild, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { SERVER_URL } from '../utils';


@Injectable({
  providedIn: 'root'
})
export class UserService implements CanActivate, CanActivateChild {

  currentUsername: string = "bob2";
  token: string;
  shareToken: string;
  role: string;
  saveVerifiedImages: boolean = false;
  moodleStructureInd: boolean = false;

  constructor(private http: HttpClient) {

    this.currentUsername = localStorage.getItem('user_id')
    this.role = localStorage.getItem('role')
    this.token = localStorage.getItem('token')

    let saveImages = localStorage.getItem('saveVerifiedImages')
    this.saveVerifiedImages = (saveImages && saveImages != "undefined") ? JSON.parse(localStorage.getItem('saveVerifiedImages')) : false

    let moodleInd = localStorage.getItem('moodleStructureInd')
    this.moodleStructureInd = (moodleInd && moodleInd != "undefined") ? JSON.parse(localStorage.getItem('moodleStructureInd')) : false
  }

  addTokens(form) {
    if (this.token) {
      form.append('token', this.token);
    }
    if (this.shareToken) {
      form.append('share_token', this.shareToken);
    }
  }

  login(username, password) {
    const formdata: FormData = new FormData();
    formdata.append('username', username);
    formdata.append('password', password);
    let url = SERVER_URL + "login"

    return this.http.post(url, formdata)
  }

  signup(username, password, role) {
    const formdata: FormData = new FormData();
    formdata.append('token', this.token);
    formdata.append('username', username);
    formdata.append('password', password);
    formdata.append('role', role);
    if (this.saveVerifiedImages) formdata.append('saveVerifiedImages', "on");
    if (this.moodleStructureInd) formdata.append('moodleStructureInd', "on");
    let url = SERVER_URL + "signup"

    return this.http.post(url, formdata)
  }

  updateSaveVerifiedImagesValue(saveVerifiedImages: boolean) {
    this.saveVerifiedImages = saveVerifiedImages;
    const formdata: FormData = new FormData();
    formdata.append('username', this.currentUsername);
    formdata.append('token', this.token);
    formdata.append('saveVerifiedImages', (+saveVerifiedImages).toString());
    const url = SERVER_URL + 'updateSaveVerifiedImages';

    return this.http.put(url, formdata);
  }

  updateMoodleStructureInd(moodleStructureInd: boolean) {
    this.moodleStructureInd = moodleStructureInd;
    const formdata: FormData = new FormData();
    formdata.append('username', this.currentUsername);
    formdata.append('token', this.token);
    formdata.append('moodleStructureInd', (+moodleStructureInd).toString());
    const url = SERVER_URL + 'updateMoodleStructureInd';

    return this.http.put(url, formdata);
  }

  loggued(): boolean {
    return this.token != null;
  }

  canActivate(route: ActivatedRouteSnapshot,
              state: RouterStateSnapshot): boolean {
    return this.loggued();
  }

  canActivateChild(route: ActivatedRouteSnapshot,
                   state: RouterStateSnapshot): boolean {
    console.log("Query params: ", route.queryParamMap);
    this.shareToken = route.queryParamMap.get('token');
    return this.loggued() || this.shareToken;
  }
}
