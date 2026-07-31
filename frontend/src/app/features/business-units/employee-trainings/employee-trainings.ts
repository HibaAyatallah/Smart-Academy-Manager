import { CommonModule } from '@angular/common';
import { Component, OnInit, TemplateRef, ViewChild, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { forkJoin } from 'rxjs';
import { finalize } from 'rxjs/operators';

import { SessionAttendance, TrainingEnrollment } from '../../../core/models/training.models';
import { TrainingService } from '../../../core/services/training.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

interface CalendarDay {
  date: string;
  label: string;
  future: boolean;
  attendance?: SessionAttendance;
}

@Component({
  selector: 'app-employee-trainings',
  standalone: true,
  imports: [
    CommonModule, MatButtonModule, MatCardModule, MatDialogModule, MatIconModule,
    MatProgressSpinnerModule, MatSnackBarModule, PageHeaderComponent,
  ],
  templateUrl: './employee-trainings.html',
  styleUrl: './employee-trainings.scss',
})
export class EmployeeTrainings implements OnInit {
  private readonly service = inject(TrainingService);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);

  @ViewChild('calendarDialog') calendarDialog!: TemplateRef<unknown>;

  trainings: TrainingEnrollment[] = [];
  attendances: SessionAttendance[] = [];
  selected: TrainingEnrollment | null = null;
  days: CalendarDay[] = [];
  isLoading = true;
  savingDate = '';
  errorMessage = '';

  ngOnInit(): void { this.load(); }

  load(): void {
    this.isLoading = true;
    this.errorMessage = '';
    forkJoin({
      enrollments: this.service.getEnrollments(),
      attendances: this.service.getAttendance(),
    }).pipe(finalize(() => this.isLoading = false)).subscribe({
      next: ({ enrollments, attendances }) => {
        this.trainings = (enrollments.results ?? []).filter(
          item => item.final_status === 'ENROLLED' || item.final_status === 'COMPLETED',
        );
        this.attendances = attendances.results ?? [];
      },
      error: () => this.errorMessage = 'Impossible de charger les formations de votre Business Unit.',
    });
  }

  openCalendar(training: TrainingEnrollment): void {
    this.selected = training;
    this.buildDays();
    this.dialog.open(this.calendarDialog, {
      width: 'min(920px, 96vw)',
      maxWidth: '96vw',
      panelClass: 'attendance-calendar-dialog',
      ariaLabel: `Calendrier de présence - ${training.training_title}`,
    });
  }

  toggle(day: CalendarDay): void {
    if (!this.selected || day.future || day.attendance?.validated || this.savingDate) return;
    const status = day.attendance?.status === 'PRESENT' ? 'ABSENT' : 'PRESENT';
    this.savingDate = day.date;
    const request = day.attendance
      ? this.service.updateAttendance(day.attendance.id, status, day.attendance.note)
      : this.service.recordAttendance(this.selected.id, day.date, status);
    request.pipe(finalize(() => this.savingDate = '')).subscribe({
      next: saved => {
        const index = this.attendances.findIndex(item => item.id === saved.id);
        if (index >= 0) this.attendances[index] = saved;
        else this.attendances.push(saved);
        this.buildDays();
        this.snack.open('Présence enregistrée.', 'Fermer', { duration: 2500 });
      },
      error: error => this.snack.open(
        error.error?.detail ?? error.error?.date?.[0] ?? 'Enregistrement impossible.',
        'Fermer',
        { duration: 4500 },
      ),
    });
  }

  status(training: TrainingEnrollment): string {
    const today = this.today();
    if (today < training.session_start_date) return 'À venir';
    if (today > training.session_end_date) return 'Terminée';
    return 'En cours';
  }

  presentDays(training: TrainingEnrollment): number {
    return this.attendances.filter(item =>
      item.enrollment === training.id && (item.status === 'PRESENT' || item.status === 'LATE'),
    ).length;
  }

  dayState(day: CalendarDay): string {
    if (day.attendance?.validated) return 'validated';
    if (day.attendance) return day.attendance.status === 'PRESENT' ? 'pending' : 'absent';
    return 'empty';
  }

  private buildDays(): void {
    if (!this.selected) return;
    const attendanceByDate = new Map(
      this.attendances
        .filter(item => item.enrollment === this.selected!.id)
        .map(item => [item.date, item]),
    );
    const cursor = this.parseDate(this.selected.session_start_date);
    const end = this.parseDate(this.selected.session_end_date);
    const today = this.today();
    const days: CalendarDay[] = [];
    while (cursor <= end) {
      const date = this.toDateKey(cursor);
      days.push({
        date,
        label: new Intl.DateTimeFormat('fr-FR', {
          weekday: 'short', day: '2-digit', month: 'short',
        }).format(cursor),
        future: date > today,
        attendance: attendanceByDate.get(date),
      });
      cursor.setDate(cursor.getDate() + 1);
    }
    this.days = days;
  }

  private today(): string { return this.toDateKey(new Date()); }
  private parseDate(value: string): Date {
    const [year, month, day] = value.split('-').map(Number);
    return new Date(year, month - 1, day);
  }
  private toDateKey(value: Date): string {
    const year = value.getFullYear();
    return `${year}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  }
}
