import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import axios from 'axios';
import AdSense from '../components/AdSense';
import AffiliateBanner from '../components/AffiliateBanner';

function Reader() {
  const { mangaId, chapterSlug } = useParams();
  const navigate = useNavigate();
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';

  useEffect(() => {
    const fetchChapter = async () => {
      try {
        const response = await axios.get(`${apiUrl}/api/chapter/${mangaId}/${chapterSlug}`);
        if (response.status === 202) {
          setError("Chapter is currently being downloaded by background workers. Please check back in a few minutes.");
        } else {
          setImages(response.data.images);

          // Update Reading History
          const token = localStorage.getItem('token');
          if (token) {
             const config = { headers: { Authorization: `Bearer ${token}` } };
             axios.post(`${apiUrl}/api/user/history`, {
               manga_id: mangaId,
               chapter_id: `${mangaId}/${chapterSlug}`
             }, config).catch(e => console.log('Failed to update history', e));
          }
        }
        setLoading(false);
      } catch (err) {
        setError('Error loading chapter. It may not exist or failed to download.');
        setLoading(false);
      }
    };
    fetchChapter();
  }, [mangaId, chapterSlug, apiUrl]);

  if (loading) return <div>Loading images...</div>;
  if (error) return <div style={{color:'red', textAlign:'center', marginTop:'50px'}}><h2>{error}</h2><button className="btn" onClick={() => navigate(`/manga/${mangaId}`)}>Go Back</button></div>;

  return (
    <div className="reader-container">
      <Helmet>
        <title>Read {chapterSlug.replace('-', ' ')} - MangaFire PRO</title>
        <meta name="description" content={`Read ${chapterSlug.replace('-', ' ')} online in high quality.`} />
      </Helmet>
      <div className="reader-controls">
        <button className="btn" onClick={() => navigate(`/manga/${mangaId}`)}>Back to Manga</button>
        <h3>{chapterSlug.replace('-', ' ')}</h3>
        <a href={`${apiUrl}/api/chapter/download/${mangaId}/${chapterSlug}`} className="btn" style={{background: '#333'}}>
          ⬇️ Download ZIP
        </a>
      </div>

      <AdSense slot="Top Reader Ad" />

      {images.map((imgUrl, index) => (
        <img
          key={index}
          src={`${apiUrl}${imgUrl}`}
          alt={`Page ${index + 1}`}
          className="reader-image"
          loading="lazy"
        />
      ))}

      <AffiliateBanner />
      <AdSense slot="Bottom Reader Ad" />

      <div style={{margin: '30px', display: 'flex', gap: '20px'}}>
        <button className="btn" onClick={() => navigate(`/manga/${mangaId}`)}>Back to Manga</button>
      </div>
    </div>
  );
}

export default Reader;
