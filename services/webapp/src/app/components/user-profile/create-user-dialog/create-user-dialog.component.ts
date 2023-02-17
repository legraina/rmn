import { Component, OnInit } from '@angular/core';
import { MatDialogRef } from '@angular/material/dialog';
import { NotificationService } from 'src/app/services/notification.service';
import { UserService } from 'src/app/services/user.service';

@Component({
  selector: 'app-create-user-dialog',
  templateUrl: './create-user-dialog.component.html',
  styleUrls: ['./create-user-dialog.component.css']
})
export class CreateUserDialogComponent implements OnInit {
  n_username: string = '';
  n_pass: string = '';
  n_passRepeat: string = '';
  n_role: string = '';
  hideNewPass: boolean = true;
  hideNewPass2: boolean = true;

  constructor(
    public notification: NotificationService,
    public dialogRef: MatDialogRef<CreateUserDialogComponent>,
    private userService: UserService
  ) {
  }

  ngOnInit(): void {
  }

  updateCharacters(event: KeyboardEvent) {
    let regex = new RegExp("^[a-zA-ZÀ-ÿ0-9.@]+$");
    if (!regex.test(event.key)) {
      event.preventDefault();
    }
  }

  attemptCreate() {
    if (this.n_username.length == 0 || this.n_pass.length == 0 || this.n_passRepeat.length == 0) {
      this.notification.showWarning("Veuillez remplir le(s) champ(s) vide(s)!", "Champ Vide");
    }
    else if (this.n_pass != this.n_passRepeat) {
      this.notification.showError("Votre mot de passe ne concordre pas à celui répété!", "Champs Non Égaux");
    }
    else if (this.n_role == '') {
      this.notification.showWarning("Veuillez choisir le type de compte!", "Type de Compte");
    } else {
      this.createAccount()
    }
  }

  private createAccount() {
    this.userService.signup(this.n_username, this.n_pass, this.n_role).subscribe((resp) => {
      this.notification.showSuccess("", "Compte Créé")
      this.dialogRef.close('');
    }, (err) => {
      this.notification.showError(err.error.response, "Erreur à la création du compte")
    }
    )
  }

}
