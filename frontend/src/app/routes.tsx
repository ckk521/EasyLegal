import { createBrowserRouter, Navigate } from "react-router";
import { UserAuthProvider, StaffAuthProvider } from "./contexts/AuthContext";
import { UserAuthGuard, StaffAuthGuard, UserGuestOnly, StaffGuestOnly } from "./components/AuthGuard";

// C端页面
import { UserLoginPage } from "./pages/c-side/LoginPage";
import { CSideLayout } from "./pages/c-side/CSideLayout";
import { AgentChat } from "./pages/c-side/AgentChat";
import { MyContracts } from "./pages/c-side/MyContracts";
import { ReportView } from "./pages/c-side/ReportView";
import { DraftsFolder } from "./pages/c-side/DraftsFolder";

// B端页面
import { StaffLoginPage } from "./pages/b-side/StaffLoginPage";
import { BSideLayout } from "./pages/b-side/BSideLayout";
import { Dashboard } from "./pages/b-side/Dashboard";
import { ContractList } from "./pages/b-side/ContractList";
import { ReviewDetail } from "./pages/b-side/ReviewDetail";
import { RuleLibrary } from "./pages/b-side/RuleLibrary";
import { StaffManagement } from "./pages/b-side/OtherPages";
import { SystemSettings } from "./pages/b-side/SystemSettings";

// C端路由
const userRoutes = {
  path: "/",
  element: (
    <UserAuthProvider>
      <UserAuthGuard>
        <CSideLayout />
      </UserAuthGuard>
    </UserAuthProvider>
  ),
  children: [
    { index: true, element: <AgentChat /> },
    { path: "history", element: <MyContracts /> },
    { path: "drafts", element: <DraftsFolder /> },
    { path: "report/:id", element: <ReportView /> },
  ],
};

// C端登录路由
const userLoginRoute = {
  path: "/login",
  element: (
    <UserAuthProvider>
      <UserGuestOnly>
        <UserLoginPage />
      </UserGuestOnly>
    </UserAuthProvider>
  ),
};

// B端路由
const staffRoutes = {
  path: "/admin",
  element: (
    <StaffAuthProvider>
      <BSideLayout />
    </StaffAuthProvider>
  ),
  children: [
    { index: true, element: <Dashboard /> },
    { path: "contracts", element: <ContractList /> },
    { path: "review/:id", element: <ReviewDetail /> },
    { path: "rules", element: <RuleLibrary /> },
    { path: "staff", element: <StaffManagement /> },
    { path: "settings", element: <SystemSettings /> },
  ],
};

// B端登录路由
const staffLoginRoute = {
  path: "/admin/login",
  element: (
    <StaffAuthProvider>
      <StaffGuestOnly>
        <StaffLoginPage />
      </StaffGuestOnly>
    </StaffAuthProvider>
  ),
};

// 默认重定向路由
const defaultRoute = {
  path: "*",
  element: <Navigate to="/" replace />,
};

export const router = createBrowserRouter([
  userLoginRoute,
  staffLoginRoute,
  userRoutes,
  staffRoutes,
  defaultRoute,
]);
