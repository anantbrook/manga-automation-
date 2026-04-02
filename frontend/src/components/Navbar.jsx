import { Link } from 'react-router-dom';

function Navbar() {
  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        🔥 MANGAFIRE PRO
      </Link>
      <div className="navbar-links">
        {/* Placeholder for future auth or extra links */}
        <input
          type="text"
          className="search-bar"
          placeholder="Search for manga..."
          onChange={(e) => console.log('Search:', e.target.value)}
        />
      </div>
    </nav>
  );
}

export default Navbar;
