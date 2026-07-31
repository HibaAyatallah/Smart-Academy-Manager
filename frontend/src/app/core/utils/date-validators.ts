import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

/**
 * Normalizes a value to a Date object set to midnight (local time) to perform date-only comparison.
 * If the value is invalid or empty, returns null.
 */
export function parseLocalDate(value: any): Date | null {
  if (!value) return null;
  const d = new Date(value);
  if (isNaN(d.getTime())) return null;
  // Reset time to midnight local time for date-only comparison
  d.setHours(0, 0, 0, 0);
  return d;
}

/**
 * Validator that ensures the date value is not earlier than today's date in local time.
 */
export function minTodayValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const val = control.value;
    if (!val) return null;
    const dateVal = parseLocalDate(val);
    if (!dateVal) return null;
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (dateVal.getTime() < today.getTime()) {
      return { minToday: true };
    }
    return null;
  };
}

/**
 * Cross-field validator to ensure that the end date control value is greater than or equal to the start date control value.
 */
export function dateRangeValidator(startControlName: string, endControlName: string): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const startCtrl = control.get(startControlName);
    const endCtrl = control.get(endControlName);
    if (!startCtrl || !endCtrl) return null;
    
    const startVal = startCtrl.value;
    const endVal = endCtrl.value;
    if (!startVal || !endVal) return null;
    
    const startDate = parseLocalDate(startVal);
    const endDate = parseLocalDate(endVal);
    if (!startDate || !endDate) return null;
    
    if (endDate.getTime() < startDate.getTime()) {
      // Set the error on the end control so it displays properly in the UI
      endCtrl.setErrors({ ...endCtrl.errors, dateRange: true });
      return { dateRange: true };
    } else {
      // Clear the dateRange error if it was previously set
      if (endCtrl.errors) {
        const { dateRange, ...otherErrors } = endCtrl.errors;
        endCtrl.setErrors(Object.keys(otherErrors).length ? otherErrors : null);
      }
    }
    return null;
  };
}
