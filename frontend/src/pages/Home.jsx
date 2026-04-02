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
        // Since we don't have a /api/manga list endpoint yet, we'll use search with empty query or fetch popular
        const response = await axios.get('http://localhost:5000/api/search/?q=');
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
