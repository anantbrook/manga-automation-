import { useState, useEffect } from 'react';
import axios from 'axios';
import MangaCard from '../components/MangaCard';
import AdSense from '../components/AdSense';
import AffiliateBanner from '../components/AffiliateBanner';

function Home() {
  const [mangas, setMangas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMangas = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';
        const response = await axios.get(`${apiUrl}/api/manga/popular`);
        setMangas(response.data);
        setLoading(false);
      } catch (error) {
        console.error("Error fetching mangas", error);
        setLoading(false);
      }
    };
    fetchMangas();
  }, []);

  return (
    <div>
      <AdSense slot="Top Header Ad" />
      <h2>Latest Updates</h2>

      {loading ? (
        <p>Loading...</p>
      ) : mangas.length === 0 ? (
        <p>No manga found. Use the admin panel to add some!</p>
      ) : (
        <div className="manga-grid">
          {mangas.map(manga => (
            <MangaCard key={manga.id} manga={manga} />
          ))}
        </div>
      )}

      <AffiliateBanner />
      <AdSense slot="Bottom Footer Ad" />
    </div>
  );
}

export default Home;
