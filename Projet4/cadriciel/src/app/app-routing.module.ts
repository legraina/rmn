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


// This is my case
const routes: Routes = [
    {
        path : '',
        component : LoginPageComponent
    },
    {
        path: 'main-menu',
        component : MainMenuComponent
    },
    {
        path: 'new-correction',
        component : NewCorrectionComponent
    },
    {
        path: 'tasks-history',
        component : TasksHistoryComponent
    },
    {
        path: 'templates',
        component : TemplatesPageComponent
    },
    {
        path: 'template-editor',
        component : TemplateEditorComponent
    },
    {
        path: 'task-validation',
        component : TaskVerificationComponent
    },
    {
        path: 'presentation-page',
        component : PresentationPageComponent
    },
    {
        path: 'user-profile',
        component : UserProfileComponent
    },
    {
        path: 'user-guide',
        component : UserGuideComponent
    }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, {
      // onSameUrlNavigation: 'reload'
  })],
  exports: [RouterModule]
})

export class AppRoutingModule { }
