import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TasksService } from 'src/app/services/tasks.service';
import { NotificationService } from 'src/app/services/notification.service';

@Component({
  selector: 'app-main-menu',
  templateUrl: './main-menu.component.html',
  styleUrls: ['./main-menu.component.css']
})
export class MainMenuComponent implements OnInit {

  constructor(
    private router: Router,
    public tasksService: TasksService,
    private notificationService: NotificationService
  ) { }

  
  async ngOnInit(): Promise<void> {
    this.tasksService.getTasks();
  }

  disconnect(): void {
    localStorage.clear()
    this.router.navigate(['/']);
    this.notificationService.showInfo("", "Déconnecté!")
  }

  newCorrection(): void {
    this.router.navigate(['/new-correction']);
  }

  goToTasksHistory(): void {
    this.router.navigate(['/tasks-history']);
  }

  goToTemplatesPage(): void {
    this.router.navigate(['/templates']);
  }

  goToPresentationPage(): void {
    this.router.navigate(['/presentation-page']);
  }

  goToProfilePage(): void {
    this.router.navigate(['/user-profile']);
  }

  goToUserGuide(): void {
    this.router.navigate(['/user-guide']);
  }

}
