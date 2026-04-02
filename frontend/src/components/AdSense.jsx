function AdSense({ slot }) {
  return (
    <div className="ad-container">
      <p>Advertisement</p>
      {/* <!-- Insert AdSense Code Here --> */}
      <small>Slot: {slot}</small>
    </div>
  );
}

export default AdSense;
