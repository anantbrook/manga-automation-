import { Link } from 'react-router-dom';

function MangaCard({ manga }) {
  return (
    <Link to={`/manga/${manga.id}`} className="manga-card">
      <img src={manga.cover_url} alt={manga.title} className="manga-cover" />
      <div className="manga-info">
        <h3 className="manga-title">{manga.title}</h3>
        <span style={{color: '#777', fontSize: '0.9rem'}}>Source: {manga.source}</span>
      </div>
    </Link>
  );
}

export default MangaCard;
