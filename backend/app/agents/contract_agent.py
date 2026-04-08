"""
法务智能体 - LLM决策 + 深度反思循环

架构：
用户输入 → [LLM思考决策] → [执行工具] → [深度反思] → [满意则输出/不满意则纠正重试]

核心改进：
1. LLM 做决策思考，理解用户意图的语义
2. 深度反思：评估结果是否真正满足用户需求
3. 自动纠正：反思不满意时自动调整策略
"""

from typing import List, Dict, Any, Optional
from pydantic.v1 import BaseModel, Field
import json
import re
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.base import BaseAgent, AgentContext
from app.agents.prompts.contract_prompts import DEFAULT_GREETING, DEFAULT_REJECTION


# ==================== 数据模型 ====================

class Decision(BaseModel):
    """LLM决策输出"""
    thinking: str = Field(description="思考过程，分析用户意图")
    action: str = Field(description="工具名称或'done'")
    args: Dict = Field(default={}, description="工具参数")
    expected_result: str = Field(description="期望的结果")


class Reflection(BaseModel):
    """反思输出"""
    thinking: str = Field(description="反思过程")
    satisfied: bool = Field(description="是否满意")
    score: float = Field(description="满意度评分 0-1")
    reason: str = Field(description="不满意的原因")
    correct_action: Optional[str] = Field(default=None, description="纠正后的工具")
    correct_args: Optional[Dict] = Field(default=None, description="纠正后的参数")
    user_question: Optional[str] = Field(default=None, description="需要追问用户的问题")


# ==================== 提示词 ====================

DECISION_PROMPT = """你是法务智能体的决策模块。

## 你的任务
分析用户意图，决定下一步操作。

## 可用工具
1. **get_template_list**: 搜索/获取模板列表
   - 参数: contract_type (合同类型，如"买卖"、"租赁"、"劳动"等)
   - 适用: 用户想看某种类型的模板

2. **get_contract_form**: 获取合同填写表单
   - 参数: contract_type, template_id (可选)
   - 适用: 用户确定要写某种合同

3. **ask_contract_type**: 展示所有合同类型选择
   - 参数: 无
   - 适用: 用户想看所有支持的合同类型，或用户要写合同但没说类型

4. **rag_search**: 法律知识检索
   - 参数: query (检索关键词)
   - 适用: 法律咨询、条款解释

5. **get_user_contracts**: 获取用户的合同列表
   - 参数: status (可选，筛选状态)
   - 适用: 查看已有合同

6. **save_contract_draft**: 保存合同草稿
   - 参数: contract_type, fields_data, template_id
   - 适用: 保存用户填写的数据

7. **export_contract**: 导出合同文档
   - 参数: draft_id, format
   - 适用: 导出合同为PDF/Word

8. **done**: 任务完成
   - 当不需要调用工具时使用

## 重要规则
1. 仔细理解用户意图的语义，不要只匹配关键词
2. 如果用户提到具体合同类型（买卖、租赁、劳动等），直接搜索该类型模板
3. 如果用户问"有没有XXX模板"、"支持XXX吗"，这是要搜索模板，不是选类型
4. 如果用户说"我要写合同"但没说类型，才需要展示类型选择

## 输出格式
返回JSON：
{
  "thinking": "分析用户意图的思考过程",
  "action": "工具名称或done",
  "args": {"参数": "值"},
  "expected_result": "期望得到什么结果"
}

## 示例
用户: "你有买卖交易相关模板吗？"
思考: 用户想知道有没有买卖交易类型的模板，应该直接搜索买卖相关的模板
输出: {"thinking": "用户询问买卖交易模板，直接搜索该类型", "action": "get_template_list", "args": {"contract_type": "买卖"}, "expected_result": "返回买卖相关的模板列表"}

用户: "我要写租赁合同"
思考: 用户明确要写租赁合同，应该获取租赁合同的填写表单
输出: {"thinking": "用户明确要写租赁合同", "action": "get_contract_form", "args": {"contract_type": "租赁"}, "expected_result": "返回租赁合同填写表单"}

用户: "你们支持什么合同？"
思考: 用户想了解平台支持哪些合同类型
输出: {"thinking": "用户想看所有支持的合同类型", "action": "ask_contract_type", "args": {}, "expected_result": "返回所有合同类型列表"}

用户: "你好"
思考: 普通打招呼，不需要调用工具
输出: {"thinking": "普通打招呼", "action": "done", "args": {}, "expected_result": "返回问候语"}
"""

REFLECTION_PROMPT = """你是法务智能体的反思评估模块。

## 你的任务
评估工具执行结果是否真正满足用户的真实需求。

## 反思问题
1. 结果是否真正满足了用户的原始需求？
2. 我对用户意图的理解是否正确？
3. 工具选择是否恰当？
4. 是否需要追问用户澄清？

## 常见问题
- 用户说"有买卖模板吗"，返回了类型选择 → 不满意，应该搜索买卖模板
- 用户说"我要写合同"，返回了模板列表 → 可能满意，也可能需要继续引导
- 工具返回失败 → 分析原因，决定重试或换工具

## 输出格式
返回JSON：
{
  "thinking": "反思过程",
  "satisfied": true/false,
  "score": 0.0-1.0,
  "reason": "不满意的原因",
  "correct_action": "纠正后的工具名（如满意则为null）",
  "correct_args": {"纠正后的参数"},
  "user_question": "需要追问用户的问题（如需要澄清）"
}

## 示例
用户意图: "有买卖模板吗"
我的决策: ask_contract_type
决策理由: 让用户选类型
实际结果: 返回了合同类型选择
反思: 用户已经说了"买卖"，我不应该让他再选类型，应该直接搜索买卖模板
输出: {"thinking": "用户已指定买卖类型，不应返回类型选择", "satisfied": false, "score": 0.3, "reason": "理解错了用户意图", "correct_action": "get_template_list", "correct_args": {"contract_type": "买卖"}}

用户意图: "我要写合同"
我的决策: ask_contract_type
实际结果: 返回了合同类型列表
反思: 用户没指定类型，返回类型选择是正确的
输出: {"thinking": "用户未指定类型，展示选择是正确的", "satisfied": true, "score": 0.9, "reason": "", "correct_action": null}
"""


class ContractAgent(BaseAgent):
    """法务智能体 - LLM决策 + 深度反思循环"""

    name: str = "contract_agent"
    description: str = "法务助理"
    system_prompt: str = "你是法务智能体。"

    # 配置
    MAX_ITERATIONS = 5  # 最大迭代次数

    def __init__(self, llm: ChatOpenAI):
        super().__init__(llm)
        self._greeting = DEFAULT_GREETING
        self._rejection = DEFAULT_REJECTION

    def set_greeting(self, greeting: str):
        self._greeting = greeting

    def set_rejection(self, rejection: str):
        self._rejection = rejection

    def get_tools(self) -> List[StructuredTool]:
        return self._create_tools()

    def _create_tools(self) -> List[StructuredTool]:
        """创建工具"""
        from app.agents.tools.contract_tools import (
            execute_rag_search,
            execute_get_user_contracts,
            execute_ask_contract_type,
            execute_get_template_list,
            execute_get_contract_form,
            execute_save_contract_draft,
            execute_export_contract,
        )

        db = self._context.db if self._context else None
        user_id = self._context.user_id if self._context else None

        tools = [
            StructuredTool.from_function(
                func=lambda query: execute_rag_search(query, db=db),
                name="rag_search",
                description="RAG检索知识库",
            ),
            StructuredTool.from_function(
                func=lambda status="": execute_get_user_contracts(status, db=db, user_id=user_id),
                name="get_user_contracts",
                description="获取用户合同列表",
            ),
            StructuredTool.from_function(
                func=lambda: execute_ask_contract_type(db=db),
                name="ask_contract_type",
                description="询问合同类型",
            ),
            StructuredTool.from_function(
                func=lambda contract_type: execute_get_template_list(contract_type, db=db),
                name="get_template_list",
                description="获取模板列表",
            ),
            StructuredTool.from_function(
                func=lambda contract_type, template_id=0: execute_get_contract_form(contract_type, template_id, db=db),
                name="get_contract_form",
                description="获取合同表单",
            ),
            StructuredTool.from_function(
                func=lambda contract_type, fields_data, template_id=0: execute_save_contract_draft(contract_type, fields_data, template_id, db=db, user_id=user_id),
                name="save_contract_draft",
                description="保存草稿",
            ),
            StructuredTool.from_function(
                func=lambda draft_id, format="pdf": execute_export_contract(draft_id, format, db=db, user_id=user_id),
                name="export_contract",
                description="导出合同",
            ),
        ]
        return tools

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """从响应中解析JSON"""
        try:
            # 尝试直接解析
            return json.loads(content)
        except:
            pass

        try:
            # 尝试提取JSON块
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # 尝试提取代码块中的JSON
            code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if code_block:
                return json.loads(code_block.group(1))
        except:
            pass

        return None

    async def _make_decision(self, user_input: str, history: List[Dict], last_result: Optional[Dict] = None) -> Decision:
        """LLM思考决策"""
        # 构建上下文
        context = ""
        if history:
            recent = history[-3:]  # 最近3轮对话
            context = "最近对话：\n" + "\n".join([
                f"{'用户' if h.get('role') == 'user' else '助手'}: {h.get('content', '')[:100]}"
                for h in recent
            ]) + "\n\n"

        if last_result:
            context += f"上一步结果: {json.dumps(last_result, ensure_ascii=False)[:500]}\n\n"

        prompt = f"""{context}用户输入: {user_input}

请分析用户意图，决定下一步操作。"""

        messages = [
            SystemMessage(content=DECISION_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await self.llm.ainvoke(messages)

        # 解析响应
        data = self._parse_json_response(response.content)
        if data:
            try:
                return Decision(**data)
            except:
                pass

        # 默认决策
        return Decision(
            thinking="无法解析响应，默认完成任务",
            action="done",
            args={},
            expected_result="返回默认响应"
        )

    async def _reflect(self, user_input: str, decision: Decision, result: Dict) -> Reflection:
        """深度反思评估"""
        prompt = f"""用户意图: {user_input}
我的决策: {decision.action}
决策参数: {json.dumps(decision.args, ensure_ascii=False)}
决策理由: {decision.thinking}
期望结果: {decision.expected_result}
实际结果: {json.dumps(result, ensure_ascii=False)[:1000]}

请评估结果是否真正满足用户需求。"""

        messages = [
            SystemMessage(content=REFLECTION_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await self.llm.ainvoke(messages)

        # 解析响应
        data = self._parse_json_response(response.content)
        if data:
            try:
                return Reflection(**data)
            except:
                pass

        # 默认满意
        return Reflection(
            thinking="无法解析反思响应，默认满意",
            satisfied=True,
            score=0.5,
            reason="",
        )

    def _execute_tool(self, tool_name: str, args: Dict) -> Dict:
        """执行工具"""
        tools = {t.name: t for t in self.get_tools()}
        tool = tools.get(tool_name)

        if not tool:
            return {"success": False, "error": f"工具 {tool_name} 不存在"}

        try:
            result = tool.invoke(args)
            if not isinstance(result, dict):
                result = {"success": True, "data": result}
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def run_with_tools(self, user_input: str, history: List[Dict] = None) -> Dict[str, Any]:
        """运行智能体 - LLM决策 + 深度反思循环"""
        if not self._context or not self._context.db:
            return {
                "content": "系统配置错误",
                "has_tool_call": False,
                "tool_calls": [],
                "tool_results": [],
            }

        if history is None:
            history = []

        tool_calls = []
        tool_results = []
        iteration = 0
        last_result = None

        while iteration < self.MAX_ITERATIONS:
            iteration += 1

            # 1. LLM决策
            decision = await self._make_decision(user_input, history, last_result)

            # 决策完成
            if decision.action == "done":
                break

            # 2. 执行工具
            result = self._execute_tool(decision.action, decision.args)

            tool_calls.append({"name": decision.action, "args": decision.args.copy()})
            tool_results.append({
                "success": result.get("success", True) if isinstance(result, dict) else True,
                "tool_name": decision.action,
                "result": result,
            })

            # 3. 深度反思
            reflection = await self._reflect(user_input, decision, result)

            if reflection.satisfied:
                # 满意，结束循环
                last_result = result
                break

            # 4. 不满意，检查是否需要纠正
            if reflection.correct_action:
                # 有纠正方案，继续循环执行纠正
                last_result = result  # 记录上一次结果用于上下文
                decision.action = reflection.correct_action
                decision.args = reflection.correct_args or {}

                # 直接执行纠正的工具
                correction_result = self._execute_tool(decision.action, decision.args)

                tool_calls.append({"name": decision.action, "args": decision.args.copy()})
                tool_results.append({
                    "success": correction_result.get("success", True) if isinstance(correction_result, dict) else True,
                    "tool_name": decision.action,
                    "result": correction_result,
                })

                last_result = correction_result

                # 再次反思纠正后的结果
                correction_reflection = await self._reflect(user_input, decision, correction_result)
                if correction_reflection.satisfied:
                    break

            elif reflection.user_question:
                # 需要追问用户
                return {
                    "content": reflection.user_question,
                    "has_tool_call": len(tool_calls) > 0,
                    "tool_calls": tool_calls,
                    "tool_results": tool_results,
                    "need_clarify": True,
                }

            else:
                # 没有纠正方案，结束
                last_result = result
                break

        # 5. 提取最终内容
        final_content = self._extract_content(last_result)

        return {
            "content": final_content,
            "has_tool_call": len(tool_calls) > 0,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "iterations": iteration,
        }

    def _extract_content(self, result: Optional[Dict]) -> str:
        """从工具结果中提取用户友好的内容"""
        if not result:
            return self._greeting

        if not isinstance(result, dict):
            return "处理完成。"

        # 检查是否成功
        if result.get("success") == False:
            return result.get("error", "处理失败")

        # 解包嵌套结构
        data = result.get("data", result)
        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        action = result.get("action") or (data.get("action") if isinstance(data, dict) else None)

        if action == "collect_contract_info":
            return data.get("message", "请填写合同信息。")

        if action in ["ask_contract_type", "show_template_list", "auto_select_template"]:
            return data.get("message", "请选择。")

        if result.get("success"):
            if isinstance(data, dict):
                return data.get("message", "好的，已处理。")

        return "处理完成。"

    def load_config_from_db(self):
        """从数据库加载配置"""
        if not self._context or not self._context.db:
            return
        try:
            from app.models.config import ConfigRejectScript
            reject = self._context.db.query(ConfigRejectScript).filter(
                ConfigRejectScript.is_active == True
            ).first()
            if reject and reject.content:
                self._rejection = reject.content
        except:
            pass
