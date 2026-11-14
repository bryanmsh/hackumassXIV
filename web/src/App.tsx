import { Route, Routes } from 'react-router';
import { AppShell } from './components/ui/AppShell';
import { ContactSheetPage } from './pages/ContactSheetPage';
import { GestureTestPage } from './pages/GestureTestPage';
import { LibraryPage } from './pages/LibraryPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ProfilesPage } from './pages/ProfilesPage';
import { ReaderPage } from './pages/ReaderPage';
import { SubjectEditorPage } from './pages/SubjectEditorPage';
import { SubjectReviewPage } from './pages/SubjectReviewPage';

/** Routes from the spec's web-app table. Router is supplied by main.tsx (or tests). */
export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<LibraryPage />} />
        <Route path="books/:id/subjects" element={<SubjectReviewPage />} />
        <Route path="pages/:id" element={<SubjectEditorPage />} />
        <Route path="profiles" element={<ProfilesPage />} />
        <Route path="books/:id/approve" element={<ContactSheetPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
      {/* The Reader is full screen and child-facing: no teacher chrome. */}
      <Route path="read/:bookId" element={<ReaderPage />} />
      {/* Hour-4 device check of Reader gestures. No data, no API calls. */}
      <Route path="gesture-test" element={<GestureTestPage />} />
    </Routes>
  );
}
