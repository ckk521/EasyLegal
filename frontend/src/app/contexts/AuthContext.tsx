/**
 * 认证上下文 - 管理C端用户和B端员工的登录状态
 */
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { userApi, staffApi, User, Staff } from '../services/api';

// C端用户认证上下文
interface UserAuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, nickname?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const UserAuthContext = createContext<UserAuthContextType | null>(null);

export function UserAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('user_token'));
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // 初始化时检查 token
    const savedToken = localStorage.getItem('user_token');
    if (savedToken) {
      // 设置临时 token 用于获取用户信息
      localStorage.setItem('token', savedToken);
      userApi.getMe()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('user_token');
          localStorage.removeItem('token');
          setToken(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (username: string, password: string) => {
    const response = await userApi.login(username, password);
    localStorage.setItem('user_token', response.token);
    localStorage.setItem('token', response.token);
    setToken(response.token);
    setUser(response.user);
  };

  const register = async (username: string, password: string, nickname?: string) => {
    await userApi.register(username, password, nickname);
    // 注册成功后自动登录
    await login(username, password);
  };

  const logout = async () => {
    try {
      await userApi.logout();
    } catch {
      // 忽略登出错误
    } finally {
      localStorage.removeItem('user_token');
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
    }
  };

  return (
    <UserAuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </UserAuthContext.Provider>
  );
}

export function useUserAuth() {
  const context = useContext(UserAuthContext);
  if (!context) {
    throw new Error('useUserAuth must be used within UserAuthProvider');
  }
  return context;
}

// B端员工认证上下文
interface StaffAuthContextType {
  staff: Staff | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<{ first_login: boolean }>;
  logout: () => Promise<void>;
}

const StaffAuthContext = createContext<StaffAuthContextType | null>(null);

export function StaffAuthProvider({ children }: { children: ReactNode }) {
  const [staff, setStaff] = useState<Staff | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('staff_token'));
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // 初始化时检查 token
    const savedToken = localStorage.getItem('staff_token');
    if (savedToken) {
      localStorage.setItem('token', savedToken);
      staffApi.getMe()
        .then(setStaff)
        .catch(() => {
          localStorage.removeItem('staff_token');
          localStorage.removeItem('token');
          setToken(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (username: string, password: string) => {
    const response = await staffApi.login(username, password);
    localStorage.setItem('staff_token', response.token);
    localStorage.setItem('token', response.token);
    setToken(response.token);
    setStaff(response.staff);
    return { first_login: response.first_login };
  };

  const logout = async () => {
    try {
      await staffApi.logout();
    } catch {
      // 忽略登出错误
    } finally {
      localStorage.removeItem('staff_token');
      localStorage.removeItem('token');
      setToken(null);
      setStaff(null);
    }
  };

  return (
    <StaffAuthContext.Provider value={{ staff, token, isLoading, login, logout }}>
      {children}
    </StaffAuthContext.Provider>
  );
}

export function useStaffAuth() {
  const context = useContext(StaffAuthContext);
  if (!context) {
    throw new Error('useStaffAuth must be used within StaffAuthProvider');
  }
  return context;
}
