import { Routes, Route } from 'react-router';
import HomePage from './pages/HomePage';
import PlayerPage from './pages/PlayerPage';
import BacktestPage from './pages/BacktestPage';
import Navbar from './components/Navbar';
import { ToastProvider } from './components/ToastProvider';

export default function App() {
  return (
    <ToastProvider>
      <div className="min-h-screen bg-bg-primary text-text-primary">
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/player/:playerId" element={<PlayerPage />} />
            <Route path="/backtest" element={<BacktestPage />} />
          </Routes>
        </main>
      </div>
    </ToastProvider>
  );
}