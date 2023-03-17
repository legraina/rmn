import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { TasksService } from 'src/app/services/tasks.service';
import { ValidationService } from 'src/app/services/validation.service';
import { SocketService } from 'src/app/services/socket.service';
import { NotificationService } from 'src/app/services/notification.service';
import { HttpClient } from '@angular/common/http';
import { ValidationWarningDialogComponent } from './validation-warning-dialog/validation-warning-dialog.component';
import { Router, ActivatedRoute } from '@angular/router';
import { UserService } from 'src/app/services/user.service';
import { SERVER_URL } from 'src/app/utils';

@Component({
  selector: 'app-task-verification',
  templateUrl: './task-verification.component.html',
  styleUrls: ['./task-verification.component.css']
})
export class TaskVerificationComponent implements OnInit {

  constructor(private tasksService: TasksService,
    private validationService: ValidationService,
    private socketService: SocketService,
    private notificationService: NotificationService,
    private http: HttpClient,
    public dialog: MatDialog,
    private router: Router,
    private route: ActivatedRoute,
    private userService: UserService) { }

  subgroup: string;
  pictureLoading: boolean = true;
  disabledValidationButton = true;
  disabledValidationcontainer = true;

  validating: boolean = false;

  job: Map<string, any>;

  initialCopyIndex: number;
  currentCopy: number;
  currentMatricule: number;
  currentTotal: number;
  currentPredictions: Map<string, number>;
  currentStatus: string;
  currentMatriculeSelection: string;
  currentMatriculeWarning: string;

  colorChosen: string;

  examsList: Array<any>;
  subExamsList: Array<number>;
  matriculeList: Array<any>;

  async ngOnInit(): Promise<any> {
    this.tasksService.setvalidatingTaskId(this.route.snapshot.queryParams['job']);
    this.subgroup = this.route.snapshot.queryParams['group'];
    this.job = await this.tasksService.getTask();
    if (this.job && this.job["job_id"]) {
      await this.getDocuments();
      this.initialCopyIndex = this.examsList[0].document_index;
      this.currentCopy = this.initialCopyIndex;
      this.checkForAvailableCopies();
      this.loadCopyInCanvas();
      this.getMatriculeList();
      this.getCurrentMatricule();
      this.getCurrentTotal();
      this.getCurrentPredictions();
      this.getCurrentStatus();
      this.setChosenColor(this.examsList[0]["status"]);

      this.disabledValidationButton = (!this.userService.token || this.job["job_status"] !== 'VALIDATION');

      this.socketService.join(this.job["job_id"]);
      this.socketService.getSocket().on('document_ready', async (params: any) => {
        await this.getDocuments();
        this.checkForAvailableCopies();

        let resp = JSON.parse(params);
        if (this.currentCopy === resp.document_index) {
          this.loadCopyInCanvas();
          this.getCurrentMatricule();
          this.getCurrentTotal();
          this.getCurrentPredictions();
          this.getCurrentStatus();
        }
      });

      if (this.userService.token) {
        this.socketService.join(this.userService.currentUsername);
        this.socketService.getSocket().on('jobs_status', async (params: any) => {
          const resp = JSON.parse(params);
          const jobId = resp.job_id;
          const jobStatus = resp.status;
          console.log(this.examsList[0].job_id, jobId, this.examsList[0].job_id === jobId);
          if (this.examsList[0].job_id === jobId) {
            this.disabledValidationButton = jobStatus !== 'VALIDATION';
          }
        });
      }
    } else {
      // reroute page
      this.notificationService.showWarning('Veuillez sélectionner une tâche valide!', 'Tâche non disponible');
      this.reroute();
    }
  }

  ngOnDestroy(): void {
    this.socketService.getSocket().off('document_ready');
    this.socketService.getSocket().off('jobs_status');
    this.socketService.disconnectSocket();
  }


  setQuestionId(question: string): string {
    return question.replace(/\s/g, '');
  }

  selectText(event): void {
    // const input = document.getElementById('text-box');
    // input.focus();
    event.target.select();
  }

  async getDocuments() {
    const formdata: FormData = new FormData();
    formdata.append('job_id', this.tasksService.getvalidatingTaskId());
    this.userService.addTokens(formdata);

    try {
      const promise = await this.http.post<any>(`${SERVER_URL}documents`, formdata).toPromise();
      this.examsList = promise['response'];
      this.subExamsList = this.examsList;
      if (this.subgroup) {
        this.subExamsList = [];
        for (let i = 0; i < this.examsList.length; i++) {
          if (this.examsList[i]['group'] === this.subgroup) {
            this.subExamsList.push(this.examsList[i]);
          }
        }
      }
    } catch (error) {
      console.log(error);
    }
  }


  loadCopyInCanvas() {
    const formdata: FormData = new FormData();
    this.userService.addTokens(formdata);
    formdata.append('job_id', this.tasksService.getvalidatingTaskId());
    formdata.append('document_index', this.currentCopy.toString());

    this.pictureLoading = true;

    if (this.examsList[this.currentIndex()]["status"] !== "NOT_READY") {
      this.http.post(`${SERVER_URL}document/download`, formdata, { responseType: 'blob' }).subscribe(
        (data) => {
          let url = window.URL.createObjectURL(data);
          let img = new Image();
          img.src = url;
          this.pictureLoading = false;
          img.onload = this.drawImageScaled.bind(null, img);
        },
        (error) => {
          console.error(error);
        });
    }
  }

  drawImageScaled(img) {

    let canvas = document.getElementById('cv') as HTMLCanvasElement;
    let ctx = canvas.getContext('2d');

    canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(img, 0, 0, img.width, img.height,     // source rectangle
      0, 0, canvas.width, canvas.height); // destination rectangle
  }

  changeCurrentCopy(copyIndex, status) {
    if (status !== "NOT_READY") {
      this.currentCopy = copyIndex;
      this.checkForAvailableCopies();
      this.loadCopyInCanvas();
      this.getCurrentMatricule();
      this.getCurrentTotal();
      this.getCurrentPredictions();
      this.getCurrentStatus();
      this.setChosenColor(status);
    }
  }

  changeCurrentExam(examIndex) {
    this.changeCurrentCopy(this.initialCopyIndex + examIndex, this.examsList[examIndex].status);
  }

  setChosenColor(status: string): void {
    if(status === "TO VALIDATE") {
      this.colorChosen = "red";
    }
    if(status === "HIGH ACCURACY") {
      this.colorChosen = "blue";
    }
    if(status === "VALIDATED") {
      this.colorChosen = "green";
    }
  }

  checkForAvailableCopies() {
    let counter = 0;
    this.examsList.forEach((exam: any) => {
      if (exam["status"] === "NOT_READY") {
        counter += 1;
      }
    });

    if (counter === this.examsList.length && !this.disabledValidationcontainer) {
      this.disabledValidationcontainer = true;
    }

    if (this.examsList[this.currentIndex()]["status"] !== "NOT_READY") {
      this.disabledValidationcontainer = false;
    }
  }

  getMatriculeList() {
    let tempList = JSON.parse(this.job["students_list"]);
    tempList = tempList.map(x => {
      x = { matricule: x['matricule'], nom: x['Nom complet'], identifiant: x['matricule'] + ' - ' + x["Nom complet"] }; return x;
    })
    this.matriculeList = tempList;
  }


  getCurrentMatricule() {
    let exam = this.examsList[this.currentIndex()];
    if (exam["status"] !== "NOT_READY") {
      this.currentMatricule = exam["matricule"];
      this.getDuplicatedMatricule();
      const matriculeRow = this.matriculeList.find(
        x => x['matricule'] === String(this.currentMatricule)
      );
      if (matriculeRow) {
        this.currentMatriculeSelection = matriculeRow['identifiant'];
      } else {
        this.currentMatriculeSelection = undefined;
      }
    }
  }

  getCurrentTotal() {
    this.currentTotal = this.examsList[this.currentIndex()]["total"];
  }

  getCurrentPredictions() {
    this.currentPredictions = this.examsList[this.currentIndex()]["subquestion_predictions"];
  }

  getCurrentStatus() {
    this.currentStatus = this.examsList[this.currentIndex()]["status"];
  }

  setValidatedStatus() {
    this.examsList[this.currentIndex()]["status"] = "VALIDATED";
  }


  async validateCurrentCopy() {
    if (!this.currentMatriculeSelection) {
      this.notificationService.showWarning('Veuillez fournir un matricule!', 'Matricule manquante');
      return;
    }
    Object.keys(this.currentPredictions).forEach(key => {
      let inputValue = (<HTMLInputElement>document.getElementById(key.replace(/\s/g, ''))).value;
      this.currentPredictions[key] = Number(inputValue);
    });
    this.examsList[this.currentIndex()]["total"] = this.currentTotal;

    let response = await this.validationService.validateDocument(
      this.tasksService.getvalidatingTaskId(),
      this.currentCopy,
      this.currentPredictions,
      this.currentMatricule,
      this.currentTotal,
      this.currentStatus);

    if (response === "OK") {
      this.setValidatedStatus();
      this.nextCopy();
    }
  }



  async validateJob() {
    let uncheckedcopy = 0;
    this.examsList.forEach((exam: any) => {
      if (exam["status"] === "TO VALIDATE") {
        uncheckedcopy += 1;
      }
    });

    if (uncheckedcopy > 0) {
      this.openwarningDialog();
    } else {
      this.disabledValidationcontainer = true;
      this.validating = true;
      let response = await this.validationService.validateJob(this.tasksService.getvalidatingTaskId(), this.userService.moodleStructureInd);
      if (response === "OK") {
        this.router.navigate(['/tasks-history']);
        let message = "La tâche est en cours de finalisation!";
        this.notificationService.showInfo(message, "Alerte!")
        // this.openTaskFilesDialog(this.tasksService.getvalidatingTaskId());
      }
    }
  }

  openwarningDialog(): void {
    let dialogRef = this.dialog.open(ValidationWarningDialogComponent, {
      width: '30%',
      height: '40%',
    })
    dialogRef.afterClosed().subscribe(async result => {
      if (result !== undefined && result === true) {
        this.disabledValidationcontainer = true;
        this.validating = true;
        let response = await this.validationService.validateJob(this.tasksService.getvalidatingTaskId(), this.userService.moodleStructureInd);
        if (response === "OK") {
          this.router.navigate(['/tasks-history']);
          const message = "La tâche est en cours de finalisation!";
          this.notificationService.showInfo(message, "Alerte!")
          // this.openTaskFilesDialog(this.tasksService.getvalidatingTaskId());
        }
      }
    });
  }

  changeMatricule(selection): void {
    this.currentMatricule = Number(selection.matricule);
    let exam = this.examsList[this.currentIndex()];
    exam["total"] = this.currentTotal;
    exam["matricule"] = String(this.currentMatricule);
    this.getDuplicatedMatricule();
  }

  getDuplicatedMatricule(): void {
    // search for duplicated matricules
    let mat = String(this.currentMatricule);
    let counter = 0;
    let warning = "";
    this.examsList.forEach((exam: any) => {
      if (exam["matricule"] === mat && exam["document_index"] !== this.currentCopy) {
        if (counter < 3) {
          if (counter > 0) {
            warning += ", ";
          }
          warning += exam["document_index"];
        } else if (counter == 3) {
          warning += " ..";
        }
        counter += 1;
      }
    });
    // update warning message for matricule
    if (counter == 0) {
      this.currentMatriculeWarning = undefined;
    } else {
      this.currentMatriculeWarning = warning;
    }
  }

  updateTotal(predictionKey, predictionValue): void {
    this.currentPredictions[predictionKey] = predictionValue;
    this.currentTotal = this.getTotal();
  }

  getTotal(): number {
    let sum = 0;
    for (const prediction of Object.keys(this.currentPredictions)) {
      sum += this.currentPredictions[prediction];
    }
    return sum;
  }

  trackByIndex(index, _): number {
    return index;
  }

  currentIndex(): number {
    return this.currentCopy - this.initialCopyIndex;
  }

  reroute() {
    this.router.navigate(['/tasks-history']);
  }

  previousCopy(): void {
    let tempIndex = this.currentIndex() - 1;
    while (tempIndex >= 0 && !this.subExamsList.includes(this.examsList[tempIndex])) {
      tempIndex --;
    }
    if (tempIndex >= 0) {
      this.changeCurrentExam(tempIndex);
    }
  }

  nextCopy(): void {
    let tempIndex = this.currentIndex() + 1;
    while (tempIndex < this.examsList.length && !this.subExamsList.includes(this.examsList[tempIndex])) {
      tempIndex ++;
    }
    if (tempIndex < this.examsList.length) {
      this.changeCurrentExam(tempIndex);
    }
  }

  loggued(): boolean {
    return this.userService.loggued();
  }

  sortNull(): void {}
}
