import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { StateService } from './state.service';

/** Sends who is acting on every call, and shows the server's reason when a permission check says no. */
export const identityInterceptor: HttpInterceptorFn = (req, next) => {
  const state = inject(StateService);
  return next(req.clone({ setHeaders: { 'X-AAVA-User': state.userId() } })).pipe(
    catchError((e: HttpErrorResponse) => {
      if (e.status === 403 && e.error?.detail) state.notify(e.error.detail);
      return throwError(() => e);
    }),
  );
};
