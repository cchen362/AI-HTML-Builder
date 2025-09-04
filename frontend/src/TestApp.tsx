import React from 'react';

function TestApp() {
  return (
    <div style={{ padding: '2rem', background: 'lightblue', height: '100vh' }}>
      <h1>Test App Working!</h1>
      <p>If you can see this, React is working properly.</p>
      <button onClick={() => alert('Click works!')}>Test Button</button>
    </div>
  );
}

export default TestApp;