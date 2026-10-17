import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/jost'
import '@fontsource-variable/noto-sans-devanagari'
import './styles/tokens.css'
import './styles/base.css'
import App from './App.tsx'
import { registerServiceWorker } from './runtime/serviceWorker'

registerServiceWorker()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
