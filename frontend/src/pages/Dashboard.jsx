import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import MangaCard from '../components/MangaCard';

function Dashboard() {
  const [bookmarks, setBookmarks] = useState([]);
  const [history, setHistory] = useState([]);
  const navigate = useNavigate();
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000';

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }

    const fetchData = async () => {
      try {
        const config = { headers: { Authorization: `Bearer ${token}` } };
        const bRes = await axios.get(`${apiUrl}/api/user/bookmarks`, config);
        setBookmarks(bRes.data);

        const hRes = await axios.get(`${apiUrl}/api/user/history`, config);
        setHistory(hRes.data);
      } catch (err) {
        console.error("Error fetching dashboard data", err);
        if (err.response?.status === 401) {
          localStorage.removeItem('token');
          navigate('/login');
        }
      }
    };
    fetchData();
  }, [navigate, apiUrl]);

  return (
    <div style={{ padding: '20px' }}>
      <h1>Welcome, {localStorage.getItem('username')}</h1>
      <button onClick={() => { localStorage.removeItem('token'); navigate('/'); }} className="btn" style={{background:'#dc143c', marginBottom: '30px'}}>
        Logout
      </button>

      <h2>Your Bookmarks</h2>
      {bookmarks.length === 0 ? <p>No bookmarks yet.</p> : (
        <div className="manga-grid">
          {bookmarks.map(m => <MangaCard key={m.id} manga={m} />)}
        </div>
      )}

      <h2 style={{marginTop: '40px'}}>Continue Reading</h2>
      {history.length === 0 ? <p>No reading history.</p> : (
        <div style={{display:'flex', flexDirection:'column', gap:'10px'}}>
          {history.map((h, i) => (
             <div key={i} style={{background:'#222', padding:'15px', borderRadius:'8px', display:'flex', justifyContent:'space-between'}}>
               <div>
                 <strong style={{color:'#ff4500'}}>{h.title}</strong> - {h.last_read_chapter}
               </div>
               <button onClick={() => navigate(`/manga/${h.manga_id}/${h.last_read_chapter}`)} className="btn">
                 Resume
               </button>
             </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Dashboard;
