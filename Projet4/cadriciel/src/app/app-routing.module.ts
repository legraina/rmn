import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
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

const loggedGuard = () => {
  return (localStorage.getItem('is_logged_in') == 'true');
};

// This is my case
const routes: Routes = [
    {
        path : '',
        component : LoginPageComponent
    },
    {
        path: 'main-menu',
        component : MainMenuComponent,
        canActivate: [loggedGuard]
    },
    {
        path: 'new-correction',
        component : NewCorrectionComponent,
        canActivate: [loggedGuard]
    },
    {
        path: 'tasks-history',
        component : TasksHistoryComponent,
        canActivate: [loggedGuard]
    },
    {
        path: 'templates',
        component : TemplatesPageComponent,
        canActivate: [loggedGuard]
    },
    {
        path: 'template-editor',
        component : TemplateEditorComponent,
        canActivate: [loggedGuard]
    },
    {
        path: 'task-validation',
        component : TaskVerificationComponent,
        canActivate: [loggedGuard]
    },
    {
        path: 'presentation-page',
        component : PresentationPageComponent,
        canActivate: [loggedGuard]
    },
    {
        path: 'user-profile',
        component : UserProfileComponent,
        canActivate: [loggedGuard]
    },
    {
        path: 'user-guide',
        component : UserGuideComponent,
        canActivate: [loggedGuard]
    },
    {
        path: '**',
        component : MainMenuComponent,
        canActivate: [loggedGuard]
    },
    {
        path: '**',
        component : LoginPageComponent
    }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, {
      // onSameUrlNavigation: 'reload'
  })],
  exports: [RouterModule]
})

export class AppRoutingModule { }
