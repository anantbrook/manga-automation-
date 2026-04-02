import { Routes, Route } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import Navbar from './components/Navbar';
// We do not import App.css to avoid clashing with the cyberpunk index.css

const Home = lazy(() => import('./pages/Home'));
const MangaDetail = lazy(() => import('./pages/MangaDetail'));
const Reader = lazy(() => import('./pages/Reader'));
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));

function App() {
  return (
    <div className="app-container dark-theme">
      <Navbar />
      <main className="main-content">
        <Suspense fallback={<div style={{padding: '50px', textAlign: 'center'}}>Loading...</div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/manga/:mangaId" element={<MangaDetail />} />
            <Route path="/manga/:mangaId/:chapterSlug" element={<Reader />} />
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<Dashboard />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}

export default App;
