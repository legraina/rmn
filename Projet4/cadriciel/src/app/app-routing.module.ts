import { NgModule } from '@angular/core';
import { Injectable } from '@angular/core';
import { RouterModule, Routes, Router, CanActivate, ActivatedRouteSnapshot,RouterStateSnapshot } from '@angular/router';
import { LoginPageComponent } from './components/login-page/login-page.component';
import { MainMenuComponent } from './components/main-menu/main-menu.component';
import { NewCorrectionComponent } from './components/new-correction/new-correction.component';
import { TasksHistoryComponent } from './components/tasks-history/tasks-history.component';
import { TemplatesPageComponent } from './components/templates-page/templates-page.component';
import { TemplateEditorComponent } from './components/template-editor/template-editor.component';
import { TaskVerificationComponent } from './components/task-verification/task-verification.component';
import { PresentationPageComponent } from './components/presentation-page/presentation-page.component';
import { UserProfileComponent } from './components/user-profile/user-profile.component';
import { UserGuideComponent } from './components/user-guide/user-guide.component';
import { UserService } from './services/user.service';


@Injectable()
export class LoggedGuardService implements CanActivate {
    constructor(private _router:Router, private userService: UserService) {}

    canActivate(route: ActivatedRouteSnapshot,
                state: RouterStateSnapshot): boolean {
        return this.userService.currentUsername != null;
    }
}


// This is my case
const routes: Routes = [
    {
        path : '',
        component : LoginPageComponent
    },
    {
        path: 'main-menu',
        component : MainMenuComponent,
        canActivate: [LoggedGuardService]
    },
    {
        path: 'new-correction',
        component : NewCorrectionComponent,
        canActivate: [LoggedGuardService]
    },
    {
        path: 'tasks-history',
        component : TasksHistoryComponent,
        canActivate: [LoggedGuardService]
    },
    {
        path: 'templates',
        component : TemplatesPageComponent,
        canActivate: [LoggedGuardService]
    },
    {
        path: 'template-editor',
        component : TemplateEditorComponent,
        canActivate: [LoggedGuardService]
    },
    {
        path: 'task-validation',
        component : TaskVerificationComponent,
        canActivate: [LoggedGuardService]
    },
    {
        path: 'presentation-page',
        component : PresentationPageComponent,
        canActivate: [LoggedGuardService]
    },
    {
        path: 'user-profile',
        component : UserProfileComponent,
        canActivate: [LoggedGuardService]
    },
    {
        path: 'user-guide',
        component : UserGuideComponent,
        canActivate: [LoggedGuardService]
    },
    {
        path: '**',
        redirectTo : 'main-menu',
        canActivate: [LoggedGuardService]
    },
    {
        path: '**',
        redirectTo : ''
    }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, {
      // onSameUrlNavigation: 'reload'
  })],
  exports: [RouterModule]
})

export class AppRoutingModule { }
