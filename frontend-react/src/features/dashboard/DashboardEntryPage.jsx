import { Navigate, useSearchParams } from 'react-router-dom';

import { useAuthStore } from '../../stores/useAuthStore';
import { getUserRole } from '../../utils/capabilities';
import { buildReactRouteForDjangoPage } from '../../routes/djangoViewRoutes';
import DashboardPage from './DashboardPage';

export default function DashboardEntryPage() {
  const [searchParams] = useSearchParams();
  const me = useAuthStore((state) => state.user);
  const djangoPage = searchParams.get('pagina');

  if (djangoPage) {
    const target = buildReactRouteForDjangoPage(getUserRole(me), djangoPage, searchParams);
    if (target) {
      return <Navigate to={target} replace />;
    }
  }

  return <DashboardPage />;
}
