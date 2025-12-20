import { Routes, Route, Navigate } from 'react-router-dom'

import About from './pages/about/About'
import Game from './pages/game/Game'
import { ROUTES } from './routes'


function App() {

  return (
    <Routes>
      <Route path={ROUTES.ABOUT} element={<About />} />
      <Route path={ROUTES.GAME} element={<Game />} />

      <Route path="*" element={<Navigate to={ROUTES.ABOUT} replace/>} />
    </Routes>
  );

}

export default App
