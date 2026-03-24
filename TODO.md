# 待开发事项

## 合同模板功能

### 自定义合同模板和字段定义（优先级：中）

**需求描述**：
B端用户应该能够：
1. 上传自定义合同模板（Word/PDF格式）
2. 在模板中标记变量位置（或自动识别留白）
3. 为模板配置对应的字段定义（字段名、类型、是否必填等）
4. 编辑已有模板的变量

**当前状态**：
- 变量格式已定义：`【变量名】`
- 前端可识别并渲染为输入框
- 缺少：B端模板编辑器、变量自动识别、字段定义管理界面

**相关文件**：
- `backend/app/api/document.py` - 模板上传接口
- `frontend/src/app/components/ContractTemplateEditor.tsx` - 模板渲染组件
- `frontend/src/app/pages/b-side/SystemSettings.tsx` - 系统设置页面（可添加模板管理入口）

---

*更新时间：2026-03-24*
