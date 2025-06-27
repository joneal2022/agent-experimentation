import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Tickets from './pages/Tickets';
import Alerts from './pages/Alerts';
import Analytics from './pages/Analytics';
import Deployments from './pages/Deployments';
import TimeTracking from './pages/TimeTracking';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tickets" element={<Tickets />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/deployments" element={<Deployments />} />
          <Route path="/time-tracking" element={<TimeTracking />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;