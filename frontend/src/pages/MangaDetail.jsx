import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import axios from 'axios';
import AdSense from '../components/AdSense';
import MangaCard from '../components/MangaCard';

function MangaDetail() {
  const { mangaId } = useParams();
  const [manga, setManga] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';

  useEffect(() => {
    const fetchManga = async () => {
      try {
        const response = await axios.get(`${apiUrl}/api/manga/${mangaId}`);
        setManga(response.data);

        const recRes = await axios.get(`${apiUrl}/api/manga/recommendations/${mangaId}`);
        setRecommendations(recRes.data);

        setLoading(false);
      } catch (err) {
        setError('Manga not found or error loading details.');
        setLoading(false);
      }
    };
    fetchManga();
  }, [mangaId, apiUrl]);

  const [isBookmarked, setIsBookmarked] = useState(false);

  const toggleBookmark = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      alert("Please login to bookmark.");
      return;
    }
    const config = { headers: { Authorization: `Bearer ${token}` } };
    try {
      if (isBookmarked) {
        await axios.delete(`${apiUrl}/api/user/bookmarks/${mangaId}`, config);
        setIsBookmarked(false);
      } else {
        await axios.post(`${apiUrl}/api/user/bookmarks`, { manga_id: mangaId }, config);
        setIsBookmarked(true);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    const checkBookmark = async () => {
      const token = localStorage.getItem('token');
      if (token && manga) {
        try {
          const config = { headers: { Authorization: `Bearer ${token}` } };
          const res = await axios.get(`${apiUrl}/api/user/bookmarks`, config);
          if (res.data.some(b => b.id === manga.id)) {
            setIsBookmarked(true);
          }
        } catch (err) {}
      }
    };
    checkBookmark();
  }, [manga, apiUrl]);

  if (loading) return <div>Loading details...</div>;
  if (error) return <div style={{color:'red'}}>{error}</div>;

  const schemaOrgJSONLD = {
    "@context": "https://schema.org",
    "@type": "ComicSeries",
    "name": manga.title,
    "description": manga.synopsis,
    "image": manga.cover_url,
    "url": window.location.href
  };

  return (
    <div>
      <Helmet>
        <title>{manga.title} - Read Online | MangaFire PRO</title>
        <meta name="description" content={`Read ${manga.title} online. ${manga.synopsis?.substring(0, 150)}...`} />
        <meta property="og:title" content={`${manga.title} - MangaFire PRO`} />
        <meta property="og:description" content={`Read ${manga.title} online for free. ${manga.synopsis?.substring(0, 150)}...`} />
        <meta property="og:image" content={manga.cover_url} />
        <script type="application/ld+json">
          {JSON.stringify(schemaOrgJSONLD)}
        </script>
      </Helmet>

      <AdSense slot="Manga Detail Top" />

      <div className="detail-header">
        <img src={manga.cover_url} alt={manga.title} className="detail-cover" />
        <div className="detail-info">
          <h1>{manga.title}</h1>
          <p style={{color: '#ff4500'}}>Source: {manga.source.toUpperCase()}</p>
          <button onClick={toggleBookmark} className="btn" style={{background: isBookmarked ? '#555' : '#ff4500', marginBottom: '15px'}}>
            {isBookmarked ? '🔖 Remove Bookmark' : '🔖 Bookmark'}
          </button>
          <div style={{background: '#222', padding: '15px', borderRadius: '8px', marginTop: '20px'}}>
            <h3>Synopsis</h3>
            <p>{manga.synopsis}</p>
          </div>
        </div>
      </div>

      <AdSense slot="Between Info and Chapters" />

      {recommendations.length > 0 && (
        <div style={{marginBottom: '40px'}}>
          <h2>🔥 You May Also Like</h2>
          <div className="manga-grid">
            {recommendations.map(m => (
              <MangaCard key={m.id} manga={m} />
            ))}
          </div>
        </div>
      )}

      <h2>Chapters ({manga.chapters.length})</h2>
      <div className="chapter-list">
        {manga.chapters.map(chap => {
          // Extract slug from chap id (e.g., solo-leveling/chapter-1)
          const slug = chap.id.split('/').pop();
          return (
            <div key={chap.id} className="chapter-item">
              <div>
                <strong>{chap.title}</strong>
                {chap.is_downloaded ?
                  <span style={{color: '#0f0', marginLeft: '10px', fontSize: '0.8rem'}}>✓ Available</span> :
                  <span style={{color: 'orange', marginLeft: '10px', fontSize: '0.8rem'}}>⏳ Downloading...</span>
                }
              </div>
              <div style={{display:'flex', gap:'10px'}}>
                <a href={`${apiUrl}/api/chapter/download/${mangaId}/${slug}`} className="btn" style={{background: '#333'}}>
                  ⬇️ Download ZIP
                </a>
                <Link to={`/manga/${mangaId}/${slug}`} className="btn">
                  Read
                </Link>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  );
}

export default MangaDetail;
