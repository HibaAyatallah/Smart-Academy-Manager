import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

export interface ScheduleInterviewDialogData {
  candidateName: string;
}

export interface ScheduleInterviewDialogResult {
  scheduled_at: string;
  location: string;
  meeting_link: string;
  notes: string;
}

@Component({
  selector: 'app-schedule-interview-dialog',
  standalone: true,
  imports: [
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
  templateUrl: './schedule-interview-dialog.component.html',
})
export class ScheduleInterviewDialogComponent {
  readonly data = inject<ScheduleInterviewDialogData>(MAT_DIALOG_DATA);
  private readonly dialogRef = inject(MatDialogRef<ScheduleInterviewDialogComponent>);
  private readonly formBuilder = inject(FormBuilder);

  readonly form = this.formBuilder.nonNullable.group({
    scheduled_at: ['', Validators.required],
    location: [''],
    meeting_link: [''],
    notes: [''],
  });

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    this.dialogRef.close({
      ...value,
      scheduled_at: new Date(value.scheduled_at).toISOString(),
    } satisfies ScheduleInterviewDialogResult);
  }

  close(): void {
    this.dialogRef.close(null);
  }
}

