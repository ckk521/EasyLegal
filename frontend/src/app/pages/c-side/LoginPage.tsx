/**
 * C端用户登录页面
 */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { MessageSquare, Eye, EyeOff } from 'lucide-react';
import { useUserAuth } from '../../contexts/AuthContext';
import { toast } from 'sonner';

export function UserLoginPage() {
  const navigate = useNavigate();
  const { login } = useUserAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    nickname: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      if (isLogin) {
        await login(formData.username, formData.password);
        toast.success('登录成功');
        navigate('/');
      } else {
        // 注册
        const response = await fetch('http://localhost:8000/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: formData.username,
            password: formData.password,
            nickname: formData.nickname || undefined,
          }),
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || '注册失败');
        }

        // 注册成功后自动登录
        await login(formData.username, formData.password);
        toast.success('注册成功');
        navigate('/');
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '操作失败');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex flex-col items-center pt-16 p-4">
      <div className="w-full max-w-md">
        {/* Logo - 固定在顶部 */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-blue-600 rounded-2xl shadow-lg shadow-blue-200 mb-3">
            <MessageSquare className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-xl font-bold text-slate-900">智能法律助手</h1>
          <p className="text-slate-500 text-sm mt-0.5">专业的法律咨询与合同服务</p>
        </div>

        {/* Form Card - 固定高度 */}
        <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-5">
            {isLogin ? '登录账号' : '注册新账号'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                用户名
              </label>
              <input
                type="text"
                required
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                placeholder="请输入用户名/手机号/邮箱"
              />
            </div>

            {/* 昵称字段 - 始终占用空间，登录时隐藏但保持高度 */}
            <div className={isLogin ? 'invisible h-0' : ''}>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                昵称 <span className="text-slate-400">(可选)</span>
              </label>
              <input
                type="text"
                value={formData.nickname}
                onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
                className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                placeholder="请输入昵称"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                密码
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={6}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all pr-10"
                  placeholder="请输入密码 (至少6位)"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-200"
            >
              {isLoading ? '处理中...' : (isLogin ? '登录' : '注册')}
            </button>
          </form>

          {/* Footer Links */}
          <div className="mt-5 text-center text-sm text-slate-500">
            {isLogin ? (
              <p>
                还没有账号？
                <button
                  type="button"
                  onClick={() => setIsLogin(false)}
                  className="text-blue-600 font-medium hover:underline ml-1"
                >
                  立即注册
                </button>
              </p>
            ) : (
              <p>
                已有账号？
                <button
                  type="button"
                  onClick={() => setIsLogin(true)}
                  className="text-blue-600 font-medium hover:underline ml-1"
                >
                  立即登录
                </button>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
