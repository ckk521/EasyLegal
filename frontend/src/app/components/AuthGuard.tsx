/**
 * 路由保护组件
 */
import { Navigate, useLocation } from 'react-router';
import { useUserAuth, useStaffAuth } from '../contexts/AuthContext';

// C端用户路由保护
export function UserAuthGuard({ children }: { children: React.ReactNode }) {
  const { user, token, isLoading } = useUserAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-500">加载中...</p>
        </div>
      </div>
    );
  }

  if (!token || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

// B端员工路由保护
export function StaffAuthGuard({ children }: { children: React.ReactNode }) {
  const { staff, token, isLoading } = useStaffAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400">加载中...</p>
        </div>
      </div>
    );
  }

  if (!token || !staff) {
    return <Navigate to="/admin/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

// C端：已登录用户禁止访问登录页
export function UserGuestOnly({ children }: { children: React.ReactNode }) {
  const { token, user } = useUserAuth();

  if (token && user) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

// B端：已登录员工禁止访问登录页
export function StaffGuestOnly({ children }: { children: React.ReactNode }) {
  const { token, staff } = useStaffAuth();

  if (token && staff) {
    return <Navigate to="/admin" replace />;
  }

  return <>{children}</>;
}
