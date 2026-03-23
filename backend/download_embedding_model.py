"""
预下载 Embedding 模型脚本

运行此脚本会下载 m3e-base 模型到项目的 data/embedding_models/ 目录
用于 Docker 部署前预下载模型

使用方法:
    cd backend
    python download_embedding_model.py
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置 HuggingFace 镜像（国内网络）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from app.config import settings
from sentence_transformers import SentenceTransformer


def download_model():
    """下载模型到指定目录"""
    model_name = "moka-ai/m3e-base"
    cache_dir = settings.DATA_DIR / "embedding_models"

    # 确保目录存在
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"正在下载模型: {model_name}")
    print(f"目标目录: {cache_dir}")
    print(f"模型大小: 约 400MB")
    print("-" * 50)

    # 下载模型
    model = SentenceTransformer(
        model_name,
        cache_folder=str(cache_dir)
    )

    print("-" * 50)
    print("✅ 模型下载完成!")
    print(f"模型保存在: {cache_dir}")

    # 测试模型
    print("\n测试模型...")
    test_text = "这是一个测试句子"
    embedding = model.encode(test_text)
    print(f"测试文本: {test_text}")
    print(f"向量维度: {len(embedding)}")
    print("✅ 模型工作正常!")


if __name__ == "__main__":
    download_model()
