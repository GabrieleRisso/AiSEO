import { Routes, Route } from 'react-router';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { Prompts } from './pages/Prompts';
import { Sources } from './pages/Sources';
import { Brands } from './pages/Brands';
import { Suggestions } from './pages/Suggestions';
import { Settings } from './pages/Settings';

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/prompts" element={<Prompts />} />
        <Route path="/sources" element={<Sources />} />
        <Route path="/brands" element={<Brands />} />
        <Route path="/suggestions" element={<Suggestions />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}

export default App;
