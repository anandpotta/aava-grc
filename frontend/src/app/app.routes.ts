import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'ask' },
  {
    path: 'ask',
    loadComponent: () => import('./features/ask/ask.component').then((m) => m.AskComponent),
    title: 'Ask AAVA',
  },
  {
    path: 'search',
    loadComponent: () => import('./features/reg-search/reg-search.component').then((m) => m.RegSearchComponent),
    title: 'Regulatory search',
  },
  {
    path: 'rules/:id',
    loadComponent: () => import('./features/rule-detail/rule-detail.component').then((m) => m.RuleDetailComponent),
    title: 'Rule detail',
  },
  {
    path: 'rulebooks',
    loadComponent: () => import('./features/rulebooks/rulebooks.component').then((m) => m.RulebooksComponent),
    title: 'Rulebooks',
  },
  {
    path: 'obligations',
    loadComponent: () => import('./features/obligations/obligations.component').then((m) => m.ObligationsComponent),
    title: 'Obligations',
  },
  {
    path: 'library',
    loadComponent: () => import('./features/library/library.component').then((m) => m.LibraryComponent),
    title: 'Controls and policies',
  },
  {
    path: 'maps',
    loadComponent: () => import('./features/compliance-map/compliance-map.component').then((m) => m.ComplianceMapComponent),
    title: 'Compliance maps',
  },
  {
    path: 'maps/:mapId',
    loadComponent: () => import('./features/compliance-map/compliance-map.component').then((m) => m.ComplianceMapComponent),
    title: 'Compliance map',
  },
  {
    path: 'reg-change',
    loadComponent: () => import('./features/reg-change/reg-change.component').then((m) => m.RegChangeComponent),
    title: 'Regulatory change management',
  },
  { path: 'scope', loadComponent: () => import('./features/scope/scope.component').then((m) => m.ScopeComponent) },
  { path: 'inbox', loadComponent: () => import('./features/inbox/inbox.component').then((m) => m.InboxComponent) },
  { path: 'story', loadComponent: () => import('./features/story/story.component').then((m) => m.StoryComponent) },
  { path: 'access', loadComponent: () => import('./features/access/access.component').then((m) => m.AccessComponent) },
  { path: '**', redirectTo: 'search' },
];
