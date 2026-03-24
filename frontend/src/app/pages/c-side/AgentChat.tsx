import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Bot,
  User,
  Plus,
  FileUp,
  Sparkles,
  FileText,
  Gavel,
  History,
  MessageSquare,
  AlertCircle,
  FileCheck,
  Download,
  ChevronRight,
  Trash2
} from "lucide-react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import { Link, useSearchParams } from "react-router";
import { useUserAuth } from "../../contexts/AuthContext";
import { ContractTemplateEditor } from "../../components/ContractTemplateEditor";

const API_BASE_URL = "http://localhost:8002";

function cn(...inputs: any[]) {
  return twMerge(clsx(inputs));
}

// 简单的ID生成器
let messageIdCounter = 0;
const generateId = () => `${Date.now()}_${++messageIdCounter}`;

interface Message {
  id: string;
  role: "bot" | "user";
  content: string;
  type?: "text" | "contract_form" | "contract_result" | "contract_template_choice" | "contract_type_selection";
  metadata?: any;
  timestamp: Date;
}

interface ContractFormData {
  contract_type: string;
  contract_type_name: string;
  has_template: boolean;
  template_id: number | null;
  fields: any[];
  greeting: string;
  template_content?: string;
}

interface TemplateChoice {
  id: number;
  name: string;
  contract_type: string;
  description: string;
  content: string;  // 模板内容，用于预览
}

interface TemplateChoiceData {
  has_templates?: boolean;
  need_type_selection?: boolean;
  contract_type?: string;
  templates?: TemplateChoice[];
  greeting: string;
  available_types?: string[];
  form?: ContractFormData;
}

interface ChatSession {
  id: number;
  title: string;
  contract_id: number | null;
  created_at: string;
  updated_at: string;
}

export function AgentChat() {
  const { user } = useUserAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [llmConfigured, setLlmConfigured] = useState<boolean | null>(null);
  const [currentForm, setCurrentForm] = useState<ContractFormData | null>(null);
  const [currentDraftId, setCurrentDraftId] = useState<number | null>(null);
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [showDraftPrompt, setShowDraftPrompt] = useState(false);
  const [loadedDraft, setLoadedDraft] = useState<any>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 会话相关状态
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // 检查LLM配置
  useEffect(() => {
    const checkLLM = async () => {
      try {
        const token = localStorage.getItem("user_token");
        const response = await fetch(`${API_BASE_URL}/api/chat/check-llm`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        if (response.ok) {
          const data = await response.json();
          setLlmConfigured(data.configured);
        }
      } catch (error) {
        console.error("检查LLM配置失败:", error);
      }
    };
    checkLLM();
  }, []);

  // 加载会话列表
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const token = localStorage.getItem("user_token");
        if (!token) return;

        const response = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (response.ok) {
          const data = await response.json();
          setSessions(data);

          // 如果有会话，自动加载最近的会话历史
          if (data.length > 0) {
            loadSessionHistory(data[0].id);
          } else {
            // 没有会话，显示欢迎消息
            setMessages([{
              id: "welcome",
              role: "bot",
              content: "您好！我是您的法律 AI 助手。我可以帮您审核合同、起草协议，或者回答法律相关问题。请问今天有什么可以帮您？",
              timestamp: new Date(),
            }]);
          }
        }
      } catch (error) {
        console.error("加载会话列表失败:", error);
        // 加载失败，显示欢迎消息
        setMessages([{
          id: "welcome",
          role: "bot",
          content: "您好！我是您的法律 AI 助手。我可以帮您审核合同、起草协议，或者回答法律相关问题。请问今天有什么可以帮您？",
          timestamp: new Date(),
        }]);
      }
    };
    loadSessions();
  }, []);

  // 加载会话历史
  const loadSessionHistory = async (sessionId: number) => {
    setIsLoadingHistory(true);
    try {
      const token = localStorage.getItem("user_token");
      const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentSessionId(sessionId);

        // 转换消息格式
        const historyMessages: Message[] = data.messages.map((m: any) => ({
          id: m.id?.toString() || generateId(),
          role: m.role === "assistant" ? "bot" : m.role,
          content: m.content,
          metadata: m.metadata,
          timestamp: new Date(m.created_at || Date.now())
        }));

        // 如果没有历史消息，显示欢迎消息
        if (historyMessages.length === 0) {
          historyMessages.push({
            id: "welcome",
            role: "bot",
            content: "您好！我是您的法律 AI 助手。我可以帮您审核合同、起草协议，或者回答法律相关问题。请问今天有什么可以帮您？",
            timestamp: new Date(),
          });
        }

        setMessages(historyMessages);
      }
    } catch (error) {
      console.error("加载会话历史失败:", error);
      toast.error("加载历史失败");
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // 创建新会话
  const handleNewSession = () => {
    setCurrentSessionId(null);
    setMessages([{
      id: "welcome",
      role: "bot",
      content: "您好！我是您的法律 AI 助手。我可以帮您审核合同、起草协议，或者回答法律相关问题。请问今天有什么可以帮您？",
      timestamp: new Date(),
    }]);
    setCurrentForm(null);
    setCurrentDraftId(null);
    setDraftValues({});
  };

  // 删除会话
  const handleDeleteSession = async (sessionId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const token = localStorage.getItem("user_token");
      const response = await fetch(`${API_BASE_URL}/api/chat/sessions/${sessionId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        setSessions(prev => prev.filter(s => s.id !== sessionId));
        if (currentSessionId === sessionId) {
          handleNewSession();
        }
        toast.success("对话已删除");
      }
    } catch (error) {
      toast.error("删除失败");
    }
  };

  // 检查未完成的草稿
  useEffect(() => {
    const checkPendingDraft = async () => {
      try {
        const token = localStorage.getItem("user_token");
        if (!token) return;

        // 检查URL参数中是否有指定的草稿ID
        const draftIdFromUrl = searchParams.get('draft');

        if (draftIdFromUrl) {
          // 从草稿夹跳转过来，加载指定草稿
          const response = await fetch(`${API_BASE_URL}/api/contract-drafts/${draftIdFromUrl}`, {
            headers: { Authorization: `Bearer ${token}` }
          });

          if (response.ok) {
            const draft = await response.json();
            if (draft && draft.status === 'draft') {
              setCurrentDraftId(draft.id);
              setDraftValues(draft.field_values || {});
              setLoadedDraft(draft);
              setShowDraftPrompt(true);
              // 清除URL参数
              setSearchParams({});
            }
          }
          return;
        }

        // 没有指定草稿，检查是否有未完成的草稿
        const response = await fetch(`${API_BASE_URL}/api/contract-drafts/pending`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (response.ok) {
          const draft = await response.json();
          if (draft) {
            setCurrentDraftId(draft.id);
            setDraftValues(draft.field_values || {});
            setLoadedDraft(draft);
            setShowDraftPrompt(true);
          }
        }
      } catch (error) {
        console.error("检查草稿失败:", error);
      }
    };
    checkPendingDraft();
  }, [searchParams]);

  // 恢复草稿
  const handleRestoreDraft = async () => {
    if (currentDraftId) {
      try {
        const token = localStorage.getItem("user_token");
        // 获取完整的草稿信息（包括模板内容）
        const response = await fetch(`${API_BASE_URL}/api/contract-drafts/${currentDraftId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (response.ok) {
          const draft = await response.json();

          // 如果草稿有关联的会话ID，先加载该会话的历史
          if (draft.session_id) {
            await loadSessionHistory(draft.session_id);
          }

          // 获取模板内容（使用公开接口）
          let templateContent = '';
          try {
            const templateResponse = await fetch(`${API_BASE_URL}/api/contract-drafts/template/${encodeURIComponent(draft.contract_type)}`);
            if (templateResponse.ok) {
              const templateData = await templateResponse.json();
              templateContent = templateData.content || '';
            }
          } catch (e) {
            console.warn("获取模板失败:", e);
          }

          // 设置表单数据
          setCurrentForm({
            contract_type: draft.contract_type,
            contract_type_name: draft.contract_type,
            has_template: !!templateContent,
            template_id: draft.template_id,
            fields: draft.fields_definition || [],
            greeting: "检测到您有未完成的合同草稿，请继续填写：",
            template_content: templateContent
          });
          setCurrentDraftId(draft.id);
          setDraftValues(draft.field_values || {});

          // 如果没有关联会话，添加一条消息显示表单
          if (!draft.session_id) {
            const formMsgId = generateId();
            setMessages(prev => [...prev, {
              id: formMsgId,
              role: "bot",
              content: "检测到您有未完成的合同草稿，请继续填写：",
              type: "contract_form",
              metadata: {
                contract_type: draft.contract_type,
                contract_type_name: draft.contract_type,
                template_content: templateContent,
                fields: draft.fields_definition || [],
                has_template: !!templateContent,
                template_id: draft.template_id
              },
              timestamp: new Date(),
            }]);
          } else {
            // 有关联会话，在历史消息后追加表单
            const formMsgId = generateId();
            setMessages(prev => [...prev, {
              id: formMsgId,
              role: "bot",
              content: "继续填写您的合同草稿：",
              type: "contract_form",
              metadata: {
                contract_type: draft.contract_type,
                contract_type_name: draft.contract_type,
                template_content: templateContent,
                fields: draft.fields_definition || [],
                has_template: !!templateContent,
                template_id: draft.template_id
              },
              timestamp: new Date(),
            }]);
          }
        }
      } catch (error) {
        console.error("恢复草稿失败:", error);
        toast.error("恢复草稿失败");
      }
    }
    setShowDraftPrompt(false);
  };

  // 忽略草稿
  const handleIgnoreDraft = async () => {
    setShowDraftPrompt(false);
    setCurrentDraftId(null);
    setDraftValues({});
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const sendMessage = useCallback(async (userMessage: string) => {
    const token = localStorage.getItem("user_token");
    if (!token) {
      toast.error("请先登录");
      return;
    }

    setIsTyping(true);

    // 创建一个空的bot消息用于流式填充
    const botMsgId = generateId();
    setMessages(prev => [...prev, {
      id: botMsgId,
      role: "bot",
      content: "",
      timestamp: new Date(),
    }]);

    try {
      abortControllerRef.current = new AbortController();

      const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: currentSessionId  // 传入当前会话ID
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error("请求失败");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));

                // 处理session_id
                if (data.session_id && !currentSessionId) {
                  setCurrentSessionId(data.session_id);
                  // 刷新会话列表
                  refreshSessions();
                }

                if (data.error) {
                  setMessages(prev => prev.map(m =>
                    m.id === botMsgId ? { ...m, content: `错误: ${data.error}` } : m
                  ));
                } else if (data.type === 'contract_type_selection') {
                  // 合同类型选择 - Agent 返回可选的合同类型列表
                  setMessages(prev => prev.map(m =>
                    m.id === botMsgId ? {
                      ...m,
                      type: 'contract_type_selection',
                      content: data.data?.message || '请选择合同类型',
                      metadata: data.data
                    } : m
                  ));
                } else if (data.type === 'template_list') {
                  // 模板列表 - Agent 返回可用模板列表
                  const templateData = data.data;
                  if (templateData.has_templates && templateData.templates?.length > 0) {
                    // 有模板，显示模板选择
                    setMessages(prev => prev.map(m =>
                      m.id === botMsgId ? {
                        ...m,
                        type: 'contract_template_choice',
                        content: templateData.message || '请选择模板',
                        metadata: {
                          greeting: templateData.message,
                          contract_type: templateData.contract_type,
                          templates: templateData.templates,
                          has_templates: true
                        }
                      } : m
                    ));
                  } else {
                    // 没有模板，直接获取表单
                    sendMessage(`帮我生成一份${templateData.contract_type}`);
                  }
                } else if (data.type === 'no_template') {
                  // 没有模板，直接显示表单
                  setMessages(prev => prev.map(m =>
                    m.id === botMsgId ? {
                      ...m,
                      type: 'contract_form',
                      content: data.data?.message || '请填写合同信息',
                      metadata: {
                        contract_type: data.data?.contract_type,
                        contract_type_name: data.data?.contract_type,
                        has_template: false,
                        template_id: null,
                        fields: [],
                        template_content: '',
                        greeting: data.data?.message
                      }
                    } : m
                  ));
                } else if (data.type === 'contract_template_choice') {
                  // 合同模板选择类型（可能是类型选择或模板选择）
                  const choiceData = data.choice;
                  if (choiceData.need_type_selection) {
                    // 需要用户选择合同类型
                    setMessages(prev => prev.map(m =>
                      m.id === botMsgId ? {
                        ...m,
                        type: 'contract_type_selection',
                        content: choiceData.greeting,
                        metadata: choiceData
                      } : m
                    ));
                  } else if (choiceData.has_templates && choiceData.templates) {
                    // 有可用模板，显示模板选择
                    setMessages(prev => prev.map(m =>
                      m.id === botMsgId ? {
                        ...m,
                        type: 'contract_template_choice',
                        content: choiceData.greeting,
                        metadata: choiceData
                      } : m
                    ));
                  } else if (choiceData.form) {
                    // 没有模板，直接显示表单
                    setMessages(prev => prev.map(m =>
                      m.id === botMsgId ? {
                        ...m,
                        type: 'contract_form',
                        content: choiceData.form.greeting,
                        metadata: choiceData.form
                      } : m
                    ));
                  }
                } else if (data.type === 'contract_form') {
                  // 合同表单类型 - Agent触发了表单
                  setMessages(prev => prev.map(m =>
                    m.id === botMsgId ? {
                      ...m,
                      type: 'contract_form',
                      content: data.clean_content || data.form.greeting,
                      metadata: data.form
                    } : m
                  ));
                } else if (data.type === 'contract_result') {
                  // 合同生成结果
                  setMessages(prev => prev.map(m =>
                    m.id === botMsgId ? {
                      ...m,
                      type: 'contract_result',
                      content: data.content,
                      metadata: data.metadata
                    } : m
                  ));
                } else if (data.done) {
                  // 流式传输完成
                } else if (data.content) {
                  // 追加内容
                  setMessages(prev => prev.map(m =>
                    m.id === botMsgId ? { ...m, content: m.content + data.content } : m
                  ));
                }
              } catch (e) {
                // 解析错误，忽略
              }
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === "AbortError") {
        // 用户取消，不做处理
      } else {
        toast.error("发送消息失败");
        setMessages(prev => prev.map(m =>
          m.id === botMsgId ? { ...m, content: "抱歉，发生了一些错误，请稍后重试。" } : m
        ));
      }
    } finally {
      setIsTyping(false);
      abortControllerRef.current = null;
    }
  }, [currentSessionId]);

  // 刷新会话列表
  const refreshSessions = async () => {
    try {
      const token = localStorage.getItem("user_token");
      const response = await fetch(`${API_BASE_URL}/api/chat/sessions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (error) {
      console.error("刷新会话列表失败:", error);
    }
  };

  const handleSend = () => {
    if (!inputValue.trim() || isTyping) return;

    const userMsg: Message = {
      id: generateId(),
      role: "user",
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    const messageToSend = inputValue;
    setInputValue("");
    sendMessage(messageToSend);
  };

  const handleUpload = () => {
    toast.info("合同上传功能开发中...");
  };

  // 处理表单保存
  const handleFormSave = (values: Record<string, string>) => {
    setDraftValues(values);
  };

  // 处理表单提交
  const handleFormSubmit = (values: Record<string, string>) => {
    // 添加用户填写信息作为消息
    const formSummary = Object.entries(values)
      .filter(([_, v]) => v)
      .map(([k, v]) => `${k}: ${v}`)
      .join('\n');

    // 添加成功消息
    const successMsg: Message = {
      id: generateId(),
      role: "bot",
      content: "合同已生成成功！您可以在「我的合同」中查看和下载。",
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, successMsg]);
    setCurrentForm(null);
    setCurrentDraftId(null);
    setDraftValues({});
  };

  // 取消表单
  const handleFormCancel = () => {
    setCurrentForm(null);
  };

  return (
    <div className="flex h-full bg-slate-50 relative overflow-hidden">
      {/* Sidebar - Recent Conversations */}
      <div className="w-80 border-r border-slate-200 bg-white flex flex-col hidden lg:flex">
        <div className="p-4 border-b border-slate-100">
          <button
            onClick={handleNewSession}
            className="w-full py-3 bg-blue-600 text-white rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-blue-700 transition-all shadow-sm"
          >
            <Plus className="w-4 h-4" />
            开启新对话
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-2 mb-2">最近对话</h3>
          {isLoadingHistory ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-sm">
              暂无对话记录
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => loadSessionHistory(session.id)}
                className={cn(
                  "p-3 rounded-xl flex items-center gap-3 cursor-pointer group transition-all",
                  currentSessionId === session.id ? "bg-blue-50 text-blue-700 border border-blue-100" : "hover:bg-slate-50 text-slate-600"
                )}
              >
                <MessageSquare className={cn("w-4 h-4 shrink-0", currentSessionId === session.id ? "text-blue-600" : "text-slate-400")} />
                <div className="flex-1 overflow-hidden">
                  <p className="text-sm font-semibold truncate">{session.title}</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    {new Date(session.updated_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(session.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 rounded transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5 text-red-500" />
                </button>
              </div>
            ))
          )}
        </div>
        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span className="text-xs font-bold text-slate-900">当前用户</span>
            </div>
            <p className="text-xs text-slate-600">
              {user?.nickname || user?.username || "未登录"}
            </p>
            {llmConfigured === false && (
              <div className="mt-2 p-2 bg-amber-50 rounded-lg">
                <p className="text-[10px] text-amber-700">⚠️ AI模型未配置</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full bg-white lg:bg-slate-50/30">
        {/* 草稿恢复提示 - 固定在顶部 */}
        <AnimatePresence>
          {showDraftPrompt && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="sticky top-0 z-20 bg-amber-50 border-b border-amber-200 p-4 shadow-sm"
            >
              <div className="max-w-4xl mx-auto flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
                <div className="flex-1">
                  <h4 className="font-bold text-amber-900">检测到未完成的合同草稿</h4>
                  <p className="text-sm text-amber-700">
                    您有一份未完成的合同草稿，是否继续填写？
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={handleRestoreDraft}
                    className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition-colors"
                  >
                    继续填写
                  </button>
                  <button
                    onClick={handleIgnoreDraft}
                    className="px-4 py-2 bg-white text-amber-700 border border-amber-300 rounded-lg text-sm font-medium hover:bg-amber-100 transition-colors"
                  >
                    稍后处理
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 lg:p-8 space-y-8">
          <AnimatePresence>
            {messages.map((msg) => (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                key={msg.id}
                className={cn(
                  "flex gap-4 max-w-4xl",
                  msg.role === "user" ? "flex-row-reverse ml-auto" : "mr-auto"
                )}
              >
                <div className={cn(
                  "w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-sm",
                  msg.role === "user" ? "bg-slate-900 text-white" : "bg-blue-600 text-white"
                )}>
                  {msg.role === "user" ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                </div>

                <div className={cn("flex flex-col gap-2", msg.role === "user" ? "items-end" : "items-start")}>
                  {/* 合同类型选择 */}
                  {msg.type === 'contract_type_selection' && msg.metadata ? (
                    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-lg max-w-lg">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                          <FileText className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-900">选择合同类型</h4>
                          <p className="text-sm text-slate-500">{msg.metadata.greeting}</p>
                        </div>
                      </div>

                      {/* 合同类型列表 */}
                      <div className="grid grid-cols-2 gap-2">
                        {msg.metadata.available_types?.map((typeItem: any) => {
                          const typeName = typeof typeItem === 'string' ? typeItem : typeItem.type;
                          const typeDesc = typeof typeItem === 'object' ? typeItem.description : '';
                          return (
                            <button
                              key={typeName}
                              onClick={() => {
                                // 用户选择了合同类型，发送消息获取模板
                                sendMessage(`我要写一份${typeName}`);
                              }}
                              className="p-3 bg-slate-50 rounded-xl border border-slate-100 hover:border-blue-300 hover:bg-blue-50 text-left transition-colors"
                            >
                              <p className="font-medium text-slate-800">{typeName}</p>
                              {typeDesc && <p className="text-xs text-slate-500">{typeDesc}</p>}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ) : msg.type === 'contract_template_choice' && msg.metadata ? (
                    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-lg max-w-lg">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                          <FileText className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-900">选择生成方式</h4>
                          <p className="text-sm text-slate-500">{msg.metadata.greeting}</p>
                        </div>
                      </div>

                      {/* 可用模板列表 - 带预览功能 */}
                      {msg.metadata.templates && msg.metadata.templates.length > 0 && (
                        <div className="mb-4 space-y-2">
                          <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">点击选择模板</p>
                          {msg.metadata.templates.map((tpl: TemplateChoice) => (
                            <button
                              key={tpl.id}
                              onClick={() => {
                                // 用户选择模板，发送消息给后端获取完整表单数据
                                sendMessage(`我选择使用「${tpl.name}」模板，模板ID是${tpl.id}`);
                              }}
                              className="w-full p-3 bg-slate-50 rounded-xl border border-slate-100 hover:border-blue-300 hover:bg-blue-50 text-left transition-colors"
                            >
                              <div className="flex items-center justify-between">
                                <div>
                                  <p className="font-medium text-slate-800">{tpl.name}</p>
                                  <p className="text-xs text-slate-500">{tpl.description}</p>
                                </div>
                                <ChevronRight className="w-4 h-4 text-slate-400" />
                              </div>
                            </button>
                          ))}
                        </div>
                      )}

                      {/* 引导式填写选项 */}
                      <div className="space-y-2">
                        <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">或者</p>
                        <button
                          onClick={() => {
                            // 用户选择引导式填写
                            setMessages(prev => prev.map(m =>
                              m.id === msg.id ? {
                                ...m,
                                type: 'contract_form',
                                content: `好的，我将引导您填写${msg.metadata.contract_type}信息。`,
                                metadata: {
                                  contract_type: msg.metadata.contract_type,
                                  contract_type_name: `${msg.metadata.contract_type}合同`,
                                  has_template: false,
                                  template_id: null,
                                  fields: [],
                                  template_content: '',
                                  greeting: `好的，我将引导您填写${msg.metadata.contract_type}信息。`
                                }
                              } : m
                            ));
                          }}
                          className="w-full p-3 bg-blue-50 border border-blue-200 rounded-xl text-left hover:bg-blue-100 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                              <FileText className="w-4 h-4 text-white" />
                            </div>
                            <div>
                              <p className="font-medium text-slate-800">引导式填写</p>
                              <p className="text-xs text-slate-500">逐步填写合同信息，系统自动生成</p>
                            </div>
                          </div>
                        </button>
                      </div>
                    </div>
                  ) : msg.type === 'contract_form' && msg.metadata ? (
                    <ContractTemplateEditor
                      contractType={msg.metadata.contract_type}
                      contractTypeName={msg.metadata.contract_type_name}
                      templateContent={msg.metadata.template_content || ''}
                      fields={msg.metadata.fields || []}
                      draftId={currentDraftId || undefined}
                      draftValues={draftValues}
                      sessionId={currentSessionId || undefined}
                      onSaveDraft={handleFormSave}
                      onSubmit={handleFormSubmit}
                      onCancel={handleFormCancel}
                    />
                  ) : msg.type === 'contract_result' ? (
                    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-lg max-w-lg">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center">
                          <FileCheck className="w-5 h-5 text-emerald-600" />
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-900">合同生成成功</h4>
                          <p className="text-sm text-slate-500">合同编号: {msg.metadata?.contract_no}</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Link
                          to="/my-contracts"
                          className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
                        >
                          <FileText className="w-4 h-4" />
                          查看合同
                        </Link>
                        <button className="flex items-center gap-2 px-4 py-2.5 bg-slate-100 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-200 transition-colors">
                          <Download className="w-4 h-4" />
                          下载
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className={cn(
                      "p-4 rounded-2xl shadow-sm text-sm leading-relaxed whitespace-pre-wrap",
                      msg.role === "user" ? "bg-slate-900 text-white" : "bg-white border border-slate-100 text-slate-800"
                    )}>
                      {msg.content || (
                        <div className="flex items-center gap-1.5">
                          <div className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce" />
                          <div className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:0.2s]" />
                          <div className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:0.4s]" />
                        </div>
                      )}
                    </div>
                  )}

                  <span className="text-[10px] text-slate-400 font-medium px-2">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </motion.div>
            ))}
            {isTyping && messages[messages.length - 1]?.content && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4">
                <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center shadow-sm">
                  <Bot className="w-5 h-5" />
                </div>
                <div className="bg-white border border-slate-100 p-4 rounded-2xl flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce" />
                  <div className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:0.2s]" />
                  <div className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:0.4s]" />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Input Area */}
        <div className="p-4 lg:p-8 bg-white lg:bg-transparent shrink-0">
          <div className="max-w-4xl mx-auto relative group">
            <div className="absolute -inset-2 bg-gradient-to-r from-blue-500/10 via-indigo-500/10 to-purple-500/10 rounded-[32px] blur-xl opacity-0 group-focus-within:opacity-100 transition-opacity" />
            <div className="relative bg-white border border-slate-200 rounded-[28px] shadow-2xl overflow-hidden focus-within:border-blue-400 transition-all flex flex-col">
              <div className="flex items-center gap-2 p-2 border-b border-slate-50 bg-slate-50/30">
                <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-white rounded-full transition-all" title="上传附件">
                  <FileUp className="w-5 h-5" />
                </button>
                <button
                  onClick={handleUpload}
                  className="p-2 text-slate-400 hover:text-blue-600 hover:bg-white rounded-full transition-all flex items-center gap-1.5"
                  title="合同审核"
                >
                  <Gavel className="w-4 h-4" />
                  <span className="text-xs font-bold hidden sm:inline">审核合同</span>
                </button>
                <div className="w-px h-4 bg-slate-200 mx-1" />
                <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-white rounded-full transition-all flex items-center gap-1.5">
                  <History className="w-4 h-4" />
                  <span className="text-xs font-bold hidden sm:inline">我的历史</span>
                </button>
              </div>
              <div className="flex items-center p-3 gap-3">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="咨询法律问题或输入您的要求..."
                  className="flex-1 bg-transparent border-none focus:ring-0 text-slate-800 text-sm resize-none py-2 px-2 max-h-32 min-h-[44px]"
                  rows={1}
                  disabled={isTyping}
                />
                <button
                  onClick={handleSend}
                  disabled={!inputValue.trim() || isTyping}
                  className={cn(
                    "w-11 h-11 rounded-2xl flex items-center justify-center transition-all shadow-lg shrink-0",
                    inputValue.trim() && !isTyping ? "bg-blue-600 text-white hover:bg-blue-700 hover:scale-105" : "bg-slate-100 text-slate-400"
                  )}
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
              <div className="px-5 py-2 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-amber-500" />
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                    {llmConfigured ? "AI 已就绪" : "AI 未配置"}
                  </span>
                </div>
                <span className="text-[10px] text-slate-400">Shift + Enter 换行</span>
              </div>
            </div>
          </div>
          <p className="text-center text-[10px] text-slate-400 mt-4 font-medium">
            © 2026 EasyVerify. 合同审核结果仅供参考，不构成正式法律建议。
          </p>
        </div>
      </div>
    </div>
  );
}
