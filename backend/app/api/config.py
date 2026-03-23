"""
配置管理 API 路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.models.config import LLMConfig, EmbeddingConfig, LegalScopeConfig, RejectScriptConfig, IntentConfig
from app.schemas.config import (
    LLMConfigCreate, LLMConfigUpdate, LLMConfigResponse,
    LLMVerifyRequest, LLMVerifyResponse,
    EmbeddingConfigCreate, EmbeddingConfigUpdate, EmbeddingConfigResponse,
    LegalScopeConfigCreate, LegalScopeConfigUpdate, LegalScopeConfigResponse,
    RejectScriptConfigCreate, RejectScriptConfigUpdate, RejectScriptConfigResponse,
    IntentConfigCreate, IntentConfigUpdate, IntentConfigResponse
)
from app.utils.security import get_current_admin

router = APIRouter(prefix="/api/admin/config", tags=["配置管理"])


# ==================== LLM 配置 ====================

@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取当前LLM配置"""
    config = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()
    if not config:
        # 返回空配置提示
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="尚未配置大模型，请先添加配置"
        )
    return config


@router.post("/llm", response_model=LLMConfigResponse)
async def create_llm_config(
    config_data: LLMConfigCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """创建LLM配置"""
    # 检查是否已存在配置
    existing = db.query(LLMConfig).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已存在配置，请使用更新接口"
        )

    config = LLMConfig(**config_data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.put("/llm", response_model=LLMConfigResponse)
async def update_llm_config(
    config_data: LLMConfigUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """更新LLM配置"""
    config = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )

    update_data = config_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


@router.post("/llm/verify", response_model=LLMVerifyResponse)
async def verify_llm_config(
    verify_data: LLMVerifyRequest,
    _: dict = Depends(get_current_admin)
):
    """验证LLM配置是否有效"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 构建验证请求 - 获取模型列表或发送简单测试请求
            headers = {
                "Authorization": f"Bearer {verify_data.api_key}",
                "Content-Type": "application/json"
            }

            # 尝试获取模型列表来验证
            models_url = f"{verify_data.base_url.rstrip('/')}/models"

            try:
                response = await client.get(models_url, headers=headers)

                if response.status_code == 200:
                    models_data = response.json()
                    model_list = models_data.get("data", [])
                    available_models = [m.get("id") for m in model_list]

                    # 检查配置的模型是否在可用列表中
                    model_available = verify_data.model_name in available_models

                    return LLMVerifyResponse(
                        success=True,
                        message="API连接成功" + (f"，模型 {verify_data.model_name} 可用" if model_available else f"，模型 {verify_data.model_name} 可能需要验证"),
                        model_info={
                            "available_models": available_models[:10],  # 只返回前10个
                            "configured_model_available": model_available
                        }
                    )
                elif response.status_code == 401:
                    return LLMVerifyResponse(
                        success=False,
                        message="API Key 无效或已过期"
                    )
                else:
                    # 如果获取模型列表失败，尝试发送一个简单的测试请求
                    test_url = f"{verify_data.base_url.rstrip('/')}/chat/completions"
                    test_payload = {
                        "model": verify_data.model_name,
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 5
                    }

                    test_response = await client.post(
                        test_url,
                        headers=headers,
                        json=test_payload
                    )

                    if test_response.status_code == 200:
                        return LLMVerifyResponse(
                            success=True,
                            message="API连接成功，模型响应正常"
                        )
                    elif test_response.status_code == 401:
                        return LLMVerifyResponse(
                            success=False,
                            message="API Key 无效或已过期"
                        )
                    elif test_response.status_code == 404:
                        return LLMVerifyResponse(
                            success=False,
                            message=f"模型 {verify_data.model_name} 不存在或不可用"
                        )
                    else:
                        error_msg = test_response.json().get("error", {}).get("message", "未知错误")
                        return LLMVerifyResponse(
                            success=False,
                            message=f"验证失败: {error_msg}"
                        )

            except httpx.ConnectError:
                return LLMVerifyResponse(
                    success=False,
                    message="无法连接到API服务器，请检查Base URL"
                )
            except httpx.TimeoutException:
                return LLMVerifyResponse(
                    success=False,
                    message="连接超时，请检查网络或Base URL"
                )

    except Exception as e:
        return LLMVerifyResponse(
            success=False,
            message=f"验证过程出错: {str(e)}"
        )


@router.post("/llm/verify-and-save", response_model=LLMConfigResponse)
async def verify_and_save_llm_config(
    config_data: LLMConfigCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """验证并保存LLM配置"""
    # 先验证
    verify_result = await verify_llm_config(
        LLMVerifyRequest(
            api_key=config_data.api_key,
            base_url=config_data.base_url,
            model_name=config_data.model_name,
            api_type=config_data.api_type
        ),
        _
    )

    if not verify_result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置验证失败: {verify_result.message}"
        )

    # 验证通过，保存配置
    config = db.query(LLMConfig).filter(LLMConfig.is_active == True).first()

    if config:
        # 更新现有配置
        config.name = config_data.name
        config.api_key = config_data.api_key
        config.base_url = config_data.base_url
        config.model_name = config_data.model_name
        config.api_type = config_data.api_type
        config.is_active = config_data.is_active
        config.last_verified_at = datetime.utcnow()
    else:
        # 创建新配置
        config = LLMConfig(
            **config_data.model_dump(),
            last_verified_at=datetime.utcnow()
        )
        db.add(config)

    db.commit()
    db.refresh(config)
    return config


# ==================== Embedding 配置 ====================

@router.get("/embedding", response_model=EmbeddingConfigResponse)
async def get_embedding_config(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取当前Embedding配置"""
    config = db.query(EmbeddingConfig).filter(EmbeddingConfig.is_active == True).first()
    if not config:
        # 创建默认配置
        config = EmbeddingConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put("/embedding", response_model=EmbeddingConfigResponse)
async def update_embedding_config(
    config_data: EmbeddingConfigUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """更新Embedding配置"""
    config = db.query(EmbeddingConfig).filter(EmbeddingConfig.is_active == True).first()
    if not config:
        config = EmbeddingConfig()
        db.add(config)

    update_data = config_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


# ==================== 法律范围配置 ====================

@router.get("/legal-scope", response_model=LegalScopeConfigResponse)
async def get_legal_scope_config(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取当前法律范围配置"""
    config = db.query(LegalScopeConfig).filter(LegalScopeConfig.is_active == True).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="尚未配置法律范围"
        )
    return config


@router.post("/legal-scope", response_model=LegalScopeConfigResponse)
async def create_legal_scope_config(
    config_data: LegalScopeConfigCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """创建法律范围配置"""
    existing = db.query(LegalScopeConfig).filter(LegalScopeConfig.is_active == True).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已存在配置，请使用更新接口"
        )

    config = LegalScopeConfig(**config_data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.put("/legal-scope", response_model=LegalScopeConfigResponse)
async def update_legal_scope_config(
    config_data: LegalScopeConfigUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """更新法律范围配置"""
    config = db.query(LegalScopeConfig).filter(LegalScopeConfig.is_active == True).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )

    update_data = config_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


# ==================== 拒绝话术配置 ====================

@router.get("/reject-script", response_model=RejectScriptConfigResponse)
async def get_reject_script_config(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取当前拒绝话术配置"""
    config = db.query(RejectScriptConfig).filter(RejectScriptConfig.is_active == True).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="尚未配置拒绝话术"
        )
    return config


@router.post("/reject-script", response_model=RejectScriptConfigResponse)
async def create_reject_script_config(
    config_data: RejectScriptConfigCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """创建拒绝话术配置"""
    existing = db.query(RejectScriptConfig).filter(RejectScriptConfig.is_active == True).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已存在配置，请使用更新接口"
        )

    config = RejectScriptConfig(**config_data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.put("/reject-script", response_model=RejectScriptConfigResponse)
async def update_reject_script_config(
    config_data: RejectScriptConfigUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """更新拒绝话术配置"""
    config = db.query(RejectScriptConfig).filter(RejectScriptConfig.is_active == True).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置不存在"
        )

    update_data = config_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


# ==================== 核心意图配置 ====================

@router.get("/intents", response_model=list[IntentConfigResponse])
async def get_intent_configs(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取所有核心意图配置"""
    configs = db.query(IntentConfig).filter(IntentConfig.is_active == True).order_by(IntentConfig.priority.desc()).all()
    return configs


@router.get("/intents/{intent_id}", response_model=IntentConfigResponse)
async def get_intent_config(
    intent_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """获取单个核心意图配置"""
    config = db.query(IntentConfig).filter(IntentConfig.id == intent_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="意图配置不存在"
        )
    return config


@router.post("/intents", response_model=IntentConfigResponse)
async def create_intent_config(
    config_data: IntentConfigCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """创建核心意图配置"""
    config = IntentConfig(**config_data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.put("/intents/{intent_id}", response_model=IntentConfigResponse)
async def update_intent_config(
    intent_id: int,
    config_data: IntentConfigUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """更新核心意图配置"""
    config = db.query(IntentConfig).filter(IntentConfig.id == intent_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="意图配置不存在"
        )

    update_data = config_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


@router.delete("/intents/{intent_id}")
async def delete_intent_config(
    intent_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin)
):
    """删除核心意图配置"""
    config = db.query(IntentConfig).filter(IntentConfig.id == intent_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="意图配置不存在"
        )

    db.delete(config)
    db.commit()
    return {"message": "删除成功"}
