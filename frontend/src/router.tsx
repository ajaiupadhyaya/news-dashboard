import { createBrowserRouter } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { Home } from './routes/Home';
import { InstrumentRoute } from './routes/InstrumentRoute';
import { IndicatorRoute } from './routes/IndicatorRoute';

export const routes: RouteObject[] = [
  { path: '/', element: <Home /> },
  { path: '/finance/:symbol', element: <InstrumentRoute /> },
  { path: '/economics/:seriesId', element: <IndicatorRoute /> },
];

export const router = createBrowserRouter(routes);
