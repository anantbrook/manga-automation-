import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import AdSense from '../components/AdSense';

function MangaDetail() {
  const { mangaId } = useParams();
  const [manga, setManga] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';

  useEffect(() => {
    const fetchManga = async () => {
      try {
        const response = await axios.get(`${apiUrl}/api/manga/${mangaId}`);
        setManga(response.data);
        setLoading(false);
      } catch (err) {
        setError('Manga not found or error loading details.');
        setLoading(false);
      }
    };
    fetchManga();
  }, [mangaId, apiUrl]);

  if (loading) return <div>Loading details...</div>;
  if (error) return <div style={{color:'red'}}>{error}</div>;

  return (
    <div>
      <AdSense slot="Manga Detail Top" />

      <div className="detail-header">
        <img src={manga.cover_url} alt={manga.title} className="detail-cover" />
        <div className="detail-info">
          <h1>{manga.title}</h1>
          <p style={{color: '#ff4500'}}>Source: {manga.source.toUpperCase()}</p>
          <div style={{background: '#222', padding: '15px', borderRadius: '8px', marginTop: '20px'}}>
            <h3>Synopsis</h3>
            <p>{manga.synopsis}</p>
          </div>
        </div>
      </div>

      <AdSense slot="Between Info and Chapters" />

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
