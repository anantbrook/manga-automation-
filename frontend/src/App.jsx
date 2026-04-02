import { BrowserRouter, Routes, Route, Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Flame, Download, ChevronLeft, ChevronRight, Moon, Sun, ShoppingCart } from 'lucide-react';
import { Helmet } from 'react-helmet-async';
import './App.css';

// Vite handles the proxy in dev. In prod we use relative paths.
const PROXY = "";

const Navbar = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('mangadex');

  const handleSearch = (e) => {
    e.preventDefault();
    if (query) navigate(`/?q=${query}&source=${source}`);
  };

  return (
    <header className="navbar">
      <Link to="/" className="logo">
        MANGA<span className="glow-text">FIRE</span> PRO
      </Link>

      <form onSubmit={handleSearch} className="search-bar">
        <select value={source} onChange={e => setSource(e.target.value)} className="source-select">
          <option value="mangadex">MangaDex</option>
          <option value="aquareader">AquaReader</option>
        </select>
        <input
          type="text"
          placeholder="Search..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit"><Search size={18} /></button>
      </form>
    </header>
  );
};

const AdBanner = () => (
  <div className="ad-container my-4">
    {/* Placeholder for Google AdSense / PropellerAds */}
    <div className="bg-neutral-900 border border-neutral-800 text-neutral-500 flex items-center justify-center p-8 rounded">
      <p className="font-mono text-sm">ADVERTISEMENT SPACE (AdSense/PropellerAds)</p>
    </div>
  </div>
);

const AffiliateBanner = () => (
  <div className="affiliate-container my-8 p-6 bg-gradient-to-r from-orange-900/20 to-red-900/20 border border-orange-500/30 rounded-xl">
    <h3 className="text-orange-500 font-bold mb-4 flex items-center gap-2">
      <ShoppingCart size={20} /> Recommended Merch
    </h3>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* Real affiliate links would go here */}
      <a href="#" className="block p-4 bg-black/50 hover:bg-black/80 border border-neutral-800 rounded transition">
        <p className="text-sm font-bold truncate">Premium Anime Hoodies</p>
        <span className="text-xs text-orange-400">Shop on Amazon</span>
      </a>
      <a href="#" className="block p-4 bg-black/50 hover:bg-black/80 border border-neutral-800 rounded transition">
        <p className="text-sm font-bold truncate">Manga Box Sets</p>
        <span className="text-xs text-orange-400">Shop on Amazon</span>
      </a>
      <a href="#" className="block p-4 bg-black/50 hover:bg-black/80 border border-neutral-800 rounded transition">
        <p className="text-sm font-bold truncate">LED Neon Signs</p>
        <span className="text-xs text-orange-400">Shop on Amazon</span>
      </a>
      <a href="#" className="block p-4 bg-black/50 hover:bg-black/80 border border-neutral-800 rounded transition">
        <p className="text-sm font-bold truncate">Collectible Figures</p>
        <span className="text-xs text-orange-400">Shop on Amazon</span>
      </a>
    </div>
  </div>
);

const Home = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || 'solo leveling';
  const source = searchParams.get('source') || 'mangadex';

  const siteUrl = window.location.origin;

  useEffect(() => {
    const fetchManga = async () => {
      setLoading(true);
      try {
        const res = await axios.get(`${PROXY}/api/search?q=${query}&source=${source}`);
        setResults(res.data);
      } catch (err) {
        console.error(err);
      }
      setLoading(false);
    };
    fetchManga();
  }, [query, source]);

  return (
    <div className="container">
      <Helmet>
        <title>{query !== 'solo leveling' ? `Search: ${query} - MangaFire PRO` : 'MangaFire PRO - Read Manga Free'}</title>
        <meta name="description" content="Read your favorite manga online for free. Cyberpunk dark mode reader. Fast downloads and multi-source scraping." />
        <meta property="og:title" content="MangaFire PRO - Read Manga Free" />
        <meta property="og:description" content="Read your favorite manga online for free. Fast downloads and multi-source scraping." />
        <meta property="og:url" content={siteUrl} />
        <meta name="twitter:card" content="summary_large_image" />
      </Helmet>

      <h2 className="page-title"><Flame className="inline mb-1 mr-2 text-orange-500"/> Results for "{query}"</h2>

      <AdBanner />

      {loading ? (
        <div className="loader"></div>
      ) : (
        <div className="manga-grid">
          {results.map((m) => (
            <Link to={`/manga/${m.source}/${m.id}`} key={m.id} className="manga-card">
              <div className="cover-wrapper">
                <img src={m.cover_url ? `${PROXY}/api/proxy-image?url=${encodeURIComponent(m.cover_url)}` : 'https://via.placeholder.com/300x400?text=No+Cover'} alt={m.title} loading="lazy" />
                <div className="source-badge">{m.source}</div>
              </div>
              <div className="info">
                <h3>{m.title}</h3>
              </div>
            </Link>
          ))}
        </div>
      )}

      <AffiliateBanner />
    </div>
  );
};

const MangaDetails = () => {
  const { source, id } = useParams();

  const [manga, setManga] = useState(null);
  const [loading, setLoading] = useState(true);

  const handleDownload = async (source, mangaId, chapterId) => {
    try {
      // Create a celery job
      const res = await axios.post(`${PROXY}/api/download/${source}/${mangaId}/${chapterId}`);
      if (res.data.job_id) {
         pollDownloadJob(res.data.job_id, source, mangaId, chapterId);
      }
    } catch(err) {
      console.error(err);
      alert('Error triggering download. Make sure Celery worker is running.');
    }
  };

  const pollDownloadJob = (jobId, source, mangaId, chapterId) => {
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${PROXY}/api/download/status/${jobId}`);
        const data = res.data;
        if (data.status === 'completed') {
           clearInterval(interval);
           window.location.href = `${PROXY}/api/download/zip/${source}/${mangaId}/${chapterId}`;
        } else if (data.status === 'error') {
           clearInterval(interval);
           alert("Download failed: " + data.error);
        }
      } catch (err) {
        clearInterval(interval);
        console.error("Polling error", err);
      }
    }, 2000);
    alert(`Download queued! Background Celery processing started. (Polling ID: ${jobId})`);
  };

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        const res = await axios.get(`${PROXY}/api/manga/${source}/${id}`);
        setManga(res.data);
      } catch (err) {
        console.error(err);
      }
      setLoading(false);
    };
    fetchDetails();
  }, [id, source]);

  if (loading) return <div className="container"><div className="loader"></div></div>;
  if (!manga) return <div className="container"><h2>Manga not found.</h2></div>;

  const coverProxy = manga.cover_url ? `${PROXY}/api/proxy-image?url=${encodeURIComponent(manga.cover_url)}` : 'https://via.placeholder.com/300x450?text=No+Cover';
  const fullUrl = `${window.location.origin}/manga/${source}/${id}`;

  // JSON-LD Schema Markup
  const schema = {
    "@context": "https://schema.org",
    "@type": "Book",
    "name": manga.title,
    "description": manga.synopsis,
    "image": coverProxy,
    "url": fullUrl,
    "author": {
      "@type": "Person",
      "name": "Unknown" // We don't scrape authors yet, but placeholder helps SEO
    },
    "bookFormat": "https://schema.org/GraphicNovel"
  };

  return (
    <div className="container">
      <Helmet>
        <title>{`${manga.title} - Read Online | MangaFire PRO`}</title>
        <meta name="description" content={manga.synopsis ? manga.synopsis.substring(0, 155) + '...' : `Read ${manga.title} manga online for free.`} />
        <meta property="og:title" content={`${manga.title} - MangaFire PRO`} />
        <meta property="og:description" content={manga.synopsis ? manga.synopsis.substring(0, 155) + '...' : `Read ${manga.title} manga online for free.`} />
        <meta property="og:image" content={coverProxy} />
        <meta property="og:url" content={fullUrl} />
        <meta name="twitter:card" content="summary_large_image" />
        <script type="application/ld+json">{JSON.stringify(schema)}</script>
      </Helmet>

      <AdBanner />

      <div className="manga-header">
        <img className="main-cover" src={coverProxy} alt={manga.title} />
        <div className="manga-info">
          <h1>{manga.title}</h1>
          <div className="meta-tags">
            <span className="tag source-tag">{manga.source}</span>
          </div>
          <p className="synopsis">{manga.synopsis}</p>

          <div className="actions mt-6">
            {manga.chapters && manga.chapters.length > 0 && (
              <Link to={`/read/${source}/${id}/${manga.chapters[manga.chapters.length-1].id}`} className="btn-primary">
                Read First Chapter
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="chapter-list-container">
        <h3 className="section-title">Chapters ({manga.chapters ? manga.chapters.length : 0})</h3>
        <div className="chapter-list">
          {manga.chapters && manga.chapters.map(c => (
            <div key={c.id} className="chapter-item">
              <Link to={`/read/${source}/${id}/${c.id}`} className="chapter-link">
                {c.title}
              </Link>
              <button className="btn-secondary text-sm flex items-center gap-1" onClick={() => handleDownload(source, id, c.id)}>
                <Download size={14} /> ZIP
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const Reader = () => {
  const { source, id, chapter } = useParams();

  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState('webtoon'); // 'webtoon' | 'paged'
  const [page, setPage] = useState(0);

  useEffect(() => {
    const fetchImages = async () => {
      try {
        const res = await axios.get(`${PROXY}/api/chapter/${source}/${id}/${chapter}`);
        setImages(res.data.images);
      } catch (err) {
        console.error(err);
      }
      setLoading(false);
    };
    fetchImages();
  }, [id, chapter, source]);

  if (loading) return <div className="reader-container"><div className="loader"></div></div>;

  return (
    <div className="reader-container">
      <Helmet>
        <title>{`Reading Chapter ${chapter} - MangaFire PRO`}</title>
        <meta name="robots" content="noindex, nofollow" /> {/* Prevent crawling individual pages to avoid thin content penalties */}
      </Helmet>

      <div className="reader-nav">
        <button onClick={() => window.history.back()} className="btn-secondary"><ChevronLeft size={18}/> Back</button>
        <div className="reader-controls">
          <button className={`btn-mode ${mode === 'webtoon' ? 'active' : ''}`} onClick={() => setMode('webtoon')}>Scroll</button>
          <button className={`btn-mode ${mode === 'paged' ? 'active' : ''}`} onClick={() => setMode('paged')}>Paged</button>
        </div>
      </div>

      {mode === 'webtoon' ? (
        <div className="webtoon-view">
          {images.map((img, i) => (
            <img key={i} src={`${PROXY}/api/proxy-image?url=${encodeURIComponent(img)}`} alt={`Page ${i+1}`} loading="lazy" />
          ))}
        </div>
      ) : (
        <div className="paged-view">
          {images.length > 0 && (
            <img src={`${PROXY}/api/proxy-image?url=${encodeURIComponent(images[page])}`} alt={`Page ${page+1}`} />
          )}
          <div className="paged-controls">
            <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="btn-secondary"><ChevronLeft/> Prev</button>
            <span>{page + 1} / {images.length}</span>
            <button disabled={page === images.length - 1} onClick={() => setPage(p => p + 1)} className="btn-secondary">Next <ChevronRight/></button>
          </div>
        </div>
      )}

      <div className="py-8">
        <AdBanner />
      </div>
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <div className="app-wrapper">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/manga/:source/:id" element={<MangaDetails />} />
            <Route path="/read/:source/:id/:chapter" element={<Reader />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
