import { Component, OnInit } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { TasksService } from 'src/app/services/tasks.service';
import { ValidationService } from 'src/app/services/validation.service';
import { SocketService } from 'src/app/services/socket.service';
import { NotificationService } from 'src/app/services/notification.service';
import { HttpClient } from '@angular/common/http';
import { TaskFilesDialogComponent } from '../tasks-history/task-files-dialog/task-files-dialog.component';
import { ValidationWarningDialogComponent } from './validation-warning-dialog/validation-warning-dialog.component';
import { Router } from '@angular/router';
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
    private userService: UserService) { }

  pictureLoading: boolean = true;
  disabledValidationButton = true;
  disabledValidationcontainer = true;

  validating: boolean = false;


  currentCopy: number;
  currentMatricule: number;
  currentTotal: number;
  currentPredictions: Map<string, number>;
  currentStatus: string;
  currentMatriculeSelection: string;

  colorChosen: string;

  examsList: Array<any>;
  matriculeList: Array<any>;

  async ngOnInit(): Promise<any> {
    this.socketService.initSocket(this.userService.currentUsername)
    this.currentCopy = 1;
    await this.getDocuments();
    this.checkForAvailableCopies();
    this.loadCopyInCanvas();
    this.getMatriculeList();
    this.getCurrentMatricule();
    this.getCurrentTotal();
    this.getCurrentPredictions();
    this.getCurrentStatus();
    this.setChosenColor(this.examsList[0]["status"]);

    const taskList = await this.tasksService.getTaskById(this.examsList[0].job_id);


    taskList.forEach((task: any) => {
      if (task.job_id === this.examsList[0].job_id) {
        this.disabledValidationButton = task.job_status !== 'VALIDATION';
      }
    });

    this.socketService.getSocket().on('document_ready', async (params: any) => {

      let resp = JSON.parse(params)

      let index = resp.document_index - 1;

      this.examsList[index]["status"] = resp.status;
      await this.getDocuments()
      /*let message = "La copie numéro #" + String(resp.document_index) + " est prête à être vérifier!";*/
      /*this.notificationService.showInfo(message, "Alerte!")*/
      this.checkForAvailableCopies();

      if (this.currentCopy === resp.document_index) {
        this.loadCopyInCanvas();
        this.getMatriculeList();
        this.getCurrentMatricule();
        this.getCurrentTotal();
        this.getCurrentPredictions();
        this.getCurrentStatus();
      }
    });

    this.socketService.getSocket().on('jobs_status', async (params: any) => {
      const resp = JSON.parse(params);

      const jobId = resp.job_id;
      const jobStatus = resp.status;
      console.log(this.examsList[0].job_id, jobId, this.examsList[0].job_id === jobId);
      if (this.examsList[0].job_id === jobId) {
        console.log('donzo');
        this.disabledValidationButton = jobStatus !== 'VALIDATION';
      }
    });
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
    formdata.append('token', this.userService.token);

    try {
      const promise = await this.http.post<any>(`${SERVER_URL}documents`, formdata).toPromise();
      this.examsList = promise['response'];
    } catch (error) {
      console.log(error);
    }

  }


  loadCopyInCanvas() {
    const formdata: FormData = new FormData();
    formdata.append('token', this.userService.token);
    formdata.append('job_id', this.tasksService.getvalidatingTaskId());
    formdata.append('document_index', this.currentCopy.toString());

    this.pictureLoading = true;

    /*
    MEEEEEEEEEEEEEEEEEDGE
    */

    if (this.examsList[this.currentCopy - 1]["status"] !== "NOT_READY") {
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

  changeCurrentCopy(index, status) {
    if (status !== "NOT_READY") {
      this.currentCopy = index;
      this.checkForAvailableCopies();
      this.loadCopyInCanvas();
      this.getCurrentMatricule();
      this.getCurrentTotal();
      this.getCurrentPredictions();
      this.getCurrentStatus();
      this.setChosenColor(status);
    }
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
    let numberCopies = this.examsList.length
    this.examsList.forEach((exam: any) => {
      if (exam["status"] === "NOT_READY") {
        counter += 1;
      }
    });

    if (counter === numberCopies && !this.disabledValidationcontainer) {
      this.disabledValidationcontainer = true;
    }

    if (this.examsList[this.currentCopy - 1]["status"] !== "NOT_READY") {
      this.disabledValidationcontainer = false;
    }
  }

  getMatriculeList() {
    this.examsList.forEach((exam: any) => {
      if (exam["document_index"] === this.currentCopy) {

        let tempList = JSON.parse(exam["students_list"])

        tempList = tempList.map(x => {
          x = { matricule: x['matricule'], nom: x['Nom complet'], identifiant: x['matricule'] + ' - ' + x["Nom complet"] }; return x;
        })
        this.matriculeList = tempList;
      }
    });
  }


  getCurrentMatricule() {
    this.examsList.forEach((exam: any) => {
      if (exam["document_index"] === this.currentCopy && exam["status"] !== "NOT_READY") {
        this.currentMatricule = exam["matricule"];
        const matriculeRow = this.matriculeList.find(
          x => x['matricule'] === String(this.currentMatricule)
        );
        if (matriculeRow) {
          this.currentMatriculeSelection = matriculeRow['identifiant'];
        } else {
          this.currentMatriculeSelection = undefined;
        }

      }
    });
  }

  getCurrentTotal() {
    this.examsList.forEach((exam: any) => {
      if (exam["document_index"] === this.currentCopy) {
        this.currentTotal = parseFloat((exam["total"] as number).toFixed(2));
      }
    });

  }

  getCurrentPredictions() {
    this.examsList.forEach((exam: any) => {
      if (exam["document_index"] === this.currentCopy) {
        this.currentPredictions = exam["subquestion_predictions"];
      }
    });
  }

  getCurrentStatus() {
    this.examsList.forEach((exam: any) => {
      if (exam["document_index"] === this.currentCopy) {
        this.currentStatus = exam["status"];
      }
    });
  }

  checkNextCopy(index: number) {
    let copyIsNotDisabled: boolean = false;
    this.examsList.forEach((exam: any) => {
      if (exam["document_index"] === index) {
        if (exam["status"] === "NOT_READY") {
          copyIsNotDisabled = true;
        }
      }
    });
    return copyIsNotDisabled;
  }

  setValidatedStatus() {
    this.examsList.forEach((exam: any) => {
      if (exam["document_index"] === this.currentCopy) {
        exam["status"] = "VALIDATED";
      }
    });
  }


  async validateCurrentCopy() {
    if (!this.currentMatriculeSelection) {
      this.notificationService.showWarning('Veuillez fournir un matricule!', 'Matricule manquante');
      return;
    }
    Object.keys(this.currentPredictions).forEach(key => {
      var inputValue = (<HTMLInputElement>document.getElementById(key.replace(/\s/g, ''))).value;
      this.currentPredictions[key] = Number(inputValue);
    });

    this.examsList.forEach((exam: any) => {
      if (exam["document_index"] === this.currentCopy) {
        exam["total"] = this.currentTotal;
      }
    });

    let response = await this.validationService.validateDocument(
      this.tasksService.getvalidatingTaskId(),
      this.currentCopy,
      this.currentPredictions,
      this.currentMatricule,
      this.currentTotal,
      this.currentStatus);

    if (response === "OK") {
      this.setValidatedStatus();
      if (this.currentCopy < this.examsList.length && !this.checkNextCopy(this.currentCopy + 1)) {
        let newIndex = this.currentCopy + 1;
        this.changeCurrentCopy(newIndex, this.examsList[newIndex -1].status);
      }
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


  openTaskFilesDialog(jobId: string): void {
    const formdata: FormData = new FormData();
    formdata.append('user_id', this.userService.currentUsername);
    formdata.append('token', this.userService.token);
    formdata.append('job_id', jobId);
    this.http.post<any>(`${SERVER_URL}job/batch/info`, formdata).subscribe(
      (data) => {
        let nbZipFile = data['response']
        this.dialog.open(TaskFilesDialogComponent, {
          width: '30%',
          height: '60%',
          data: { taskId: jobId, nbZipFile: nbZipFile }
        });
      });
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

    this.examsList.forEach((exam: any) => {
      if (exam["document_index"] === this.currentCopy) {
        exam["total"] = this.currentTotal;
        exam["matricule"] = String(this.currentMatricule);
      }
    });
  }

  updateTotal(predictionKey, predictionValue): void {
    this.currentPredictions[predictionKey] = predictionValue;

    let sum = 0;

    for (const prediction of Object.keys(this.currentPredictions)) {
      sum += this.currentPredictions[prediction];
    }

    this.currentTotal = +sum.toFixed(2);

  }

  trackByIndex(index, _): number {
    return index;
  }

  reroute() {
    this.router.navigate(['/tasks-history']);
  }

  previousCopy(): void {
    if (this.currentCopy > 1) {
      const tempCurrentCopy = this.currentCopy - 1;
      this.changeCurrentCopy(this.currentCopy - 1, this.examsList[tempCurrentCopy - 1].status);
    }
  }

  nextCopy(): void {
    if (this.currentCopy < this.examsList.length) {
      const tempCurrentCopy = this.currentCopy + 1;
      this.changeCurrentCopy(this.currentCopy + 1, this.examsList[tempCurrentCopy - 1].status);
    }
  }

  sortNull(): void {}
}
