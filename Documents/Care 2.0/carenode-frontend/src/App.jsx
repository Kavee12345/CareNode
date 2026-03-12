import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './app/layout';
import HomePage from './app/page';
import IntakePage from './app/intake/page';
import DashboardPage from './app/dashboard/page';
import './styles/globals.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="intake" element={<IntakePage />} />
          <Route path="dashboard" element={<DashboardPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

