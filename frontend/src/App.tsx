import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Templates from './pages/Templates'
import Agents from './pages/Agents'
import Workflows from './pages/Workflows'
import Simulation from './pages/Simulation'
import Evaluations from './pages/Evaluations'
import Settings from './pages/Settings'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="templates" element={<Templates />} />
          <Route path="agents" element={<Agents />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="simulation" element={<Simulation />} />
          <Route path="evaluations" element={<Evaluations />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
