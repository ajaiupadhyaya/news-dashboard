import { createBrowserRouter } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { Home } from './routes/Home';
import { InstrumentRoute } from './routes/InstrumentRoute';

export const routes: RouteObject[] = [
  { path: '/', element: <Home /> },
  { path: '/finance/:symbol', element: <InstrumentRoute /> },
];

export const router = createBrowserRouter(routes);
