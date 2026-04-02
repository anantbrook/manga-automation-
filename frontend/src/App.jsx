import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import MangaDetail from './pages/MangaDetail';
import Reader from './pages/Reader';
import Navbar from './components/Navbar';
import './App.css';

function App() {
  return (
    <div className="app-container dark-theme">
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/manga/:mangaId" element={<MangaDetail />} />
          <Route path="/manga/:mangaId/:chapterSlug" element={<Reader />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
