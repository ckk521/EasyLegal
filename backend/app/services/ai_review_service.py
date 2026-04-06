"""
AI合同审核服务

提供合同风险识别、条款检查等功能
采用分步审核，实时返回进度
"""
import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class AIReviewService:
    """AI合同审核服务"""

    # 审核步骤定义
    REVIEW_STEPS = [
        {
            "id": "basic_info",
            "name": "基本信息审核",
            "progress": 20,
            "prompt": """请审核合同的基本信息是否完整、规范。

检查项目：
1. 合同标题是否明确
2. 甲乙双方信息是否完整（名称、地址、联系方式）
3. 合同签订日期、生效日期是否明确

注意：合同编号由系统自动生成，无需检查。

重点检查信息完整性：
- 信息表述必须清晰明确，不能只有代码或缩写
- 例如："甲方为A"、"地址为1" 这种表述是不合格的
- 联系方式应具体（电话号码、详细地址等），不能只有"电话"二字

请以JSON格式输出审核结果：
```json
{
  "risk_items": [
    {
      "id": "B1",
      "level": "high/medium/low",
      "type": "basic_info",
      "title": "问题标题",
      "reason": "问题原因",
      "original_text": "合同中需要修改的原文内容（精确复制）",
      "suggested_text": "建议修改后的完整文本"
    }
  ]
}
```

重要说明：
- original_text 必须是合同中的原文，精确复制，用于定位和替换
- suggested_text 是修改后的完整文本，用户确认后可直接替换原文
- 如果问题无法精确定位原文（如缺失信息），original_text 可为空，suggested_text 填写建议添加的内容
- 如果没有问题，返回空的risk_items数组
- 只输出JSON，不要其他内容"""
        },
        {
            "id": "clause_legality",
            "name": "条款合法性检查",
            "progress": 40,
            "prompt": """请审核合同条款的合法性。

检查项目：
1. 是否存在违反法律法规的条款
2. 是否存在显失公平的条款
3. 是否存在霸王条款
4. 违约责任是否对等

请以JSON格式输出审核结果：
```json
{
  "risk_items": [
    {
      "id": "L1",
      "level": "high/medium/low",
      "type": "risk_clause",
      "title": "问题标题",
      "reason": "风险原因",
      "original_text": "合同中存在问题的条款原文（精确复制）",
      "suggested_text": "修改后的合法合规条款文本"
    }
  ]
}
```

重要说明：
- original_text 必须是合同中的原文，精确复制，用于定位和替换
- suggested_text 是修改后的完整文本，确保合法合规
- 如果没有问题，返回空的risk_items数组
- 只输出JSON，不要其他内容"""
        },
        {
            "id": "amount_date",
            "name": "金额/日期校验",
            "progress": 60,
            "prompt": """请审核合同中的金额和日期相关内容。

检查项目：
1. 金额是否明确、计算是否正确
2. 付款方式、付款时间是否清晰明确
3. 日期是否合理（开始日期早于结束日期等）
4. 金额大小写是否一致

重点检查信息完整性问题：
- 付款方式不能只有数字代码（如"付款方式为3"），必须有明确说明（如"银行转账"、"现金支付"等）
- 金额不能只有数字，应有单位（元、万元等）
- 日期格式应统一且明确
- 任何涉及金额、时间、数量的条款，表述必须完整清晰，不能让读者产生疑问

对于信息不完整、表述不清的内容，必须标记为风险项。

请以JSON格式输出审核结果：
```json
{
  "risk_items": [
    {
      "id": "A1",
      "level": "high/medium/low",
      "type": "amount_error",
      "title": "问题标题",
      "reason": "问题原因",
      "original_text": "合同中存在问题的金额/日期原文（精确复制）",
      "suggested_text": "修正后的金额/日期文本"
    }
  ]
}
```

重要说明：
- original_text 必须是合同中的原文，精确复制，用于定位和替换
- suggested_text 是修正后的完整文本，必须明确清晰
- 如果问题无法给出具体修正建议（如缺少付款方式说明），suggested_text 可填写"需补充明确的付款方式说明"
- 如果没有问题，返回空的risk_items数组
- 只输出JSON，不要其他内容"""
        },
        {
            "id": "missing_clause",
            "name": "缺失条款检查",
            "progress": 80,
            "prompt": """请检查合同是否缺失必要条款。

检查项目：
1. 是否有争议解决条款
2. 是否有保密条款（如需要）
3. 是否有违约责任条款
4. 是否有合同变更/解除条款
5. 是否有不可抗力条款

请以JSON格式输出审核结果：
```json
{
  "risk_items": [
    {
      "id": "M1",
      "level": "high/medium/low",
      "type": "missing_clause",
      "title": "缺失条款名称",
      "reason": "缺失原因及影响",
      "original_text": "",
      "suggested_text": "建议添加的完整条款内容（包含条款标题和正文）"
    }
  ]
}
```

重要说明：
- 缺失条款的 original_text 为空字符串
- suggested_text 填写建议添加的完整条款，格式规范，可直接插入合同
- 如果没有问题，返回空的risk_items数组
- 只输出JSON，不要其他内容"""
        },
        {
            "id": "comprehensive",
            "name": "综合评估",
            "progress": 100,
            "prompt": """请对合同进行综合评估。

评估项目：
1. 合同整体结构是否合理
2. 条款表述是否清晰、无歧义
3. 双方权利义务是否平衡
4. 风险防控措施是否到位

重点检查信息清晰度问题：
- 是否存在只有数字代码而无说明的内容（如"方式为3"、"类型为A"等）
- 是否存在无法理解的占位符、临时标记、TODO注释
- 是否存在表述模糊、可能产生歧义的条款
- 关键信息（金额、时间、责任、义务）是否表述完整明确

对于任何让读者产生疑问、无法独立理解的内容，必须标记为风险项。

请以JSON格式输出审核结果：
```json
{
  "risk_items": [
    {
      "id": "C1",
      "level": "high/medium/low",
      "type": "comprehensive",
      "title": "问题标题",
      "reason": "评估原因",
      "original_text": "合同中需要改进的原文内容（精确复制）",
      "suggested_text": "改进后的完整文本"
    }
  ],
  "overall_assessment": "合同整体评估意见（简短）"
}
```

重要说明：
- original_text 必须是合同中的原文，精确复制
- suggested_text 是改进后的完整文本
- 如果没有问题，返回空的risk_items数组
- 只输出JSON，不要其他内容"""
        }
    ]

    def __init__(self, api_key: str, base_url: str, model: str):
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.1,
            api_key=api_key,
            base_url=base_url,
            request_timeout=60  # 单个请求超时60秒
        )

    async def review_contract_stream(
        self,
        contract_content: str,
        contract_type: str = "通用合同"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        分步审核合同，流式返回进度

        Yields:
            进度消息，格式：{"step": 步骤名, "progress": 进度, "status": "processing/done", "risk_items": [...]}
        """
        all_risk_items = []

        for step in self.REVIEW_STEPS:
            # 发送开始处理的消息
            yield {
                "step": step["name"],
                "progress": step["progress"],
                "status": "processing",
                "message": f"正在进行{step['name']}..."
            }

            # 构建审核消息
            user_message = f"""合同类型：{contract_type}

合同内容：
{contract_content}

{step['prompt']}"""

            try:
                # 调用LLM（带超时保护）
                messages = [
                    HumanMessage(content=user_message)
                ]
                response = await asyncio.wait_for(
                    self.llm.ainvoke(messages),
                    timeout=90  # 总超时90秒
                )
                content = response.content

                # 解析结果
                result = self._parse_response(content)
                step_risk_items = result.get("risk_items", [])

                # 为每个风险项添加来源步骤
                for item in step_risk_items:
                    item["step"] = step["name"]
                    item["step_id"] = step["id"]

                all_risk_items.extend(step_risk_items)

                # 发送完成消息
                yield {
                    "step": step["name"],
                    "progress": step["progress"],
                    "status": "done",
                    "risk_items": step_risk_items,
                    "found_count": len(step_risk_items)
                }

            except asyncio.TimeoutError:
                # 超时错误，跳过此步骤继续
                yield {
                    "step": step["name"],
                    "progress": step["progress"],
                    "status": "timeout",
                    "message": f"{step['name']}超时，已跳过"
                }
            except Exception as e:
                # 发送错误消息，但继续执行后续步骤
                yield {
                    "step": step["name"],
                    "progress": step["progress"],
                    "status": "error",
                    "message": f"{step['name']}出错: {str(e)}"
                }

        # 发送最终结果
        risk_summary = {
            "high": sum(1 for item in all_risk_items if item.get("level") == "high"),
            "medium": sum(1 for item in all_risk_items if item.get("level") == "medium"),
            "low": sum(1 for item in all_risk_items if item.get("level") == "low")
        }

        yield {
            "step": "完成",
            "progress": 100,
            "status": "complete",
            "risk_summary": risk_summary,
            "risk_items": all_risk_items
        }

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            json_str = self._extract_json(content)
            result = json.loads(json_str)
            if "risk_items" not in result:
                result["risk_items"] = []

            # 确保 risk_items 是列表
            if not isinstance(result["risk_items"], list):
                result["risk_items"] = []

            # 过滤掉"合格"的项目，只保留有问题的
            result["risk_items"] = self._filter_risk_items(result["risk_items"])
            return result
        except (json.JSONDecodeError, TypeError):
            return {"risk_items": []}

    def _filter_risk_items(self, items) -> List[Dict]:
        """过滤风险项，移除合格/正常的项目"""
        # 确保输入是列表
        if not isinstance(items, list):
            return []

        # 表示通过的级别关键词
        pass_levels = {"合格", "pass", "ok", "normal", "none", "无", "正常", "通过"}

        # 表示通过的标题/内容关键词
        pass_keywords = [
            "合格", "正常", "通过", "符合", "无误", "完整", "规范", "正确", "无问题",
            "合理", "清晰", "明确", "到位", "平衡", "完善", "健全", "恰当", "适当"
        ]

        # 表示无需修改的建议
        no_action_keywords = ["无需修改", "无需调整", "无需更改", "无建议", "不需修改", "不用修改"]

        filtered = []
        for item in items:
            # 确保每个元素是字典
            if not isinstance(item, dict):
                continue

            level = item.get("level", "")
            if isinstance(level, str):
                level = level.lower()
            else:
                level = str(level).lower() if level else ""

            title = item.get("title", "")
            if not isinstance(title, str):
                title = str(title) if title else ""

            content = item.get("content", "") or item.get("reason", "")
            if not isinstance(content, str):
                content = str(content) if content else ""

            suggestion = item.get("suggestion", "")
            if not isinstance(suggestion, str):
                suggestion = str(suggestion) if suggestion else ""

            original_text = item.get("original_text", "")
            if not isinstance(original_text, str):
                original_text = str(original_text) if original_text else ""

            suggested_text = item.get("suggested_text", "")
            if not isinstance(suggested_text, str):
                suggested_text = str(suggested_text) if suggested_text else ""

            # 跳过级别为通过的项
            if level in pass_levels:
                continue

            # 跳过标题包含通过关键词的项
            title_lower = title.lower()
            if any(kw in title_lower for kw in pass_keywords):
                continue

            # 跳过建议为"无需修改"的项
            suggestion_lower = suggestion.lower()
            if any(kw in suggestion_lower for kw in no_action_keywords) or suggestion_lower in ["无", "无。", "暂无"]:
                continue

            # 跳过内容表示"没问题"的项
            content_lower = content.lower()
            if any(kw in content_lower for kw in pass_keywords):
                continue

            # 跳过原文和建议完全一样的项（说明原文已经是正确的，AI误判）
            if original_text and suggested_text:
                # 去除空格和标点差异后比较
                clean_original = original_text.replace(" ", "").replace("　", "")
                clean_suggested = suggested_text.replace(" ", "").replace("　", "")
                if clean_original == clean_suggested:
                    continue

                # 检测无效建议：原文已包含大写金额，建议只是添加括号重复说明
                # 例如：原文"月租金为人民币壹仟元整。" 建议"月租金为人民币壹仟元整（大写：人民币壹仟元整）"
                if self._is_redundant_amount_suggestion(original_text, suggested_text):
                    continue

                # 检测建议是否只是对原文的格式微调（如加括号、加冒号说明等）
                if self._is_meaningless_format_change(original_text, suggested_text):
                    continue

            # 只保留有效的风险级别
            if level in ["high", "medium", "low"]:
                filtered.append(item)

        return filtered

    def _is_redundant_amount_suggestion(self, original: str, suggested: str) -> bool:
        """
        检测是否为冗余的金额大写建议
        例如：原文已有大写金额，建议只是添加括号重复说明
        """
        # 大写金额字符
        chinese_amount_chars = set("壹贰叁肆伍陆柒捌玖拾佰仟万亿零整圆元角分")

        # 检查原文是否已包含大写金额
        original_has_chinese_amount = any(c in chinese_amount_chars for c in original)
        if not original_has_chinese_amount:
            return False

        # 提取原文中的金额数字部分
        import re
        # 匹配大写金额模式
        amount_pattern = r'[壹贰叁肆伍陆柒捌玖拾佰仟万亿零]+[圆元整角分]*'
        original_amounts = re.findall(amount_pattern, original)
        suggested_amounts = re.findall(amount_pattern, suggested)

        # 如果建议中的金额和原文中的金额完全一样（只是位置或格式不同）
        if original_amounts and suggested_amounts:
            # 去重后比较
            original_unique = set(original_amounts)
            suggested_unique = set(suggested_amounts)
            # 如果建议的金额都在原文中存在，且没有新增金额
            if suggested_unique.issubset(original_unique) or suggested_unique == original_unique:
                # 检查建议是否只是添加了括号或说明文字
                # 去掉括号及其内容后比较
                clean_suggested = re.sub(r'[（(][^）)]*[）)]', '', suggested)
                clean_suggested = re.sub(r'[【\[][^\]\]]*[\]】]', '', clean_suggested)
                clean_original = re.sub(r'[（(][^）)]*[）)]', '', original)
                clean_original = re.sub(r'[【\[][^\]\]]*[\]】]', '', original)

                # 如果去掉括号后核心内容一致，则是冗余建议
                if clean_original.strip() in clean_suggested.strip() or clean_suggested.strip() in clean_original.strip():
                    return True

        return False

    def _is_meaningless_format_change(self, original: str, suggested: str) -> bool:
        """
        检测是否为无意义的格式调整
        例如：只是添加括号说明、添加冒号等，核心内容没变
        """
        import re

        # 去掉所有空白字符和标点符号，比较核心内容
        def remove_format_chars(text):
            # 去掉空白
            text = re.sub(r'\s+', '', text)
            # 去掉常见格式标点
            text = re.sub(r'[，。！？、；：""''（）【】《》\[\]{}:,\.!?;\'\"]', '', text)
            return text

        clean_original = remove_format_chars(original)
        clean_suggested = remove_format_chars(suggested)

        # 如果核心内容完全一致
        if clean_original == clean_suggested:
            return True

        # 如果原文是建议的子集，且建议只是添加了说明性文字
        if clean_original in clean_suggested:
            # 计算添加的内容比例
            added_ratio = (len(clean_suggested) - len(clean_original)) / max(len(clean_original), 1)
            # 如果添加的内容不超过原文50%，可能是无意义的格式调整
            if added_ratio <= 0.5:
                return True

        # 检测"大写："、"小写："这类重复说明
        redundant_patterns = [
            r'大写[：:][^）)]+',
            r'小写[：:][^）)]+',
            r'（大写[：:].*）',
            r'（小写[：:].*）',
        ]

        # 检查建议是否只是在原文基础上添加了这类说明
        temp_suggested = suggested
        for pattern in redundant_patterns:
            temp_suggested = re.sub(pattern, '', temp_suggested)

        temp_suggested = remove_format_chars(temp_suggested)
        if temp_suggested == clean_original:
            return True

        return False

    async def format_contract(
        self,
        contract_content: str,
        contract_type: str = "通用合同"
    ) -> Dict[str, Any]:
        """
        格式化合同内容，提高可读性

        Returns:
            格式化后的合同内容
        """
        prompt = f"""请对以下合同内容进行格式化整理。

合同类型：{contract_type}

【最重要规则 - 必须严格遵守】

签字区域（包含"甲方签字"、"乙方签字"、"日期"等内容）必须是合同的**绝对最后部分**。

如果原文中签字区域后面还有任何条款内容，必须将这些条款移到签字区域之前，并重新编号。

错误示例（禁止出现）：
```
甲方签字：xxx
乙方签字：xxx

保密条款：xxx  ← 错误！签字后不能有条款
变更条款：xxx  ← 错误！签字后不能有条款
```

正确示例：
```
九、合同生效
十、保密条款：xxx
十一、变更条款：xxx

甲方签字：xxx
乙方签字：xxx  ← 签字必须是最后
```

【格式化步骤】

第一步：找出签字区域
- 找到包含"甲方签字"、"乙方签字"的行
- 这些行及其后面的日期行组成签字区域

第二步：检查签字区域后是否还有内容
- 如果有，将这些内容移到签字区域之前
- 为移动的内容分配新的条款编号

第三步：输出格式化后的合同
- 条款编号统一使用"一、二、三..."
- 保持原文内容不变，只调整顺序和格式

合同内容：
{contract_content}

请输出格式化后的合同内容："""

        try:
            messages = [HumanMessage(content=prompt)]
            response = await asyncio.wait_for(
                self.llm.ainvoke(messages),
                timeout=120
            )
            formatted_content = response.content.strip()

            return {
                "success": True,
                "original_content": contract_content,
                "formatted_content": formatted_content
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "格式化超时，请稍后重试"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_json(self, content: str) -> str:
        """从响应内容中提取JSON"""
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()

        if "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()

        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            return content[start:end+1]

        return content


# 全局服务实例
_ai_review_service: Optional[AIReviewService] = None


def get_ai_review_service(db=None) -> AIReviewService:
    """获取AI审核服务实例"""
    global _ai_review_service

    # 每次都重新创建实例，确保使用最新的代码
    if db is not None:
        from app.models.config import LLMConfig
        config = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()
        if config:
            _ai_review_service = AIReviewService(
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model_name
            )
            return _ai_review_service

    import os
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    _ai_review_service = AIReviewService(
        api_key=api_key,
        base_url=base_url,
        model=model
    )
    return _ai_review_service
