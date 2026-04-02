import { Link, useNavigate } from 'react-router-dom';

function Navbar() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const username = localStorage.getItem('username');

  return (
    <nav className="navbar" style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
      <Link to="/" className="navbar-brand">
        🔥 MANGAFIRE PRO
      </Link>

      <div style={{flex: 1, margin: '0 20px'}}>
        <input
          type="text"
          className="search-bar"
          placeholder="Search for manga... (Coming Soon)"
          style={{width: '100%', maxWidth: '400px'}}
          onChange={(e) => console.log('Search:', e.target.value)}
        />
      </div>

      <div className="navbar-links" style={{display:'flex', gap:'15px', alignItems:'center'}}>
        {token ? (
          <>
            <span style={{color: '#aaa'}}>Hi, {username}</span>
            <button onClick={() => navigate('/dashboard')} className="btn" style={{padding: '5px 15px', fontSize: '1rem'}}>Dashboard</button>
          </>
        ) : (
          <button onClick={() => navigate('/login')} className="btn" style={{padding: '5px 15px', fontSize: '1rem'}}>Login / Register</button>
        )}
      </div>
    </nav>
  );
}

export default Navbar;
