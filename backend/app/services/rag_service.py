"""
RAG 服务模块 - 向量检索
"""
import os
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from pathlib import Path

# 设置 HuggingFace 镜像（国内网络加速）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
# 优先使用本地缓存，避免每次都联网验证
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.models.config import EmbeddingConfig
from app.config import settings


class RAGService:
    """RAG 服务"""

    _instance = None
    _embeddings = None
    _vectorstore = None

    # 模型缓存目录（项目根目录下）
    MODEL_CACHE_DIR = settings.DATA_DIR / "embedding_models"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_embeddings(cls, db: Session = None) -> HuggingFaceEmbeddings:
        """获取 Embedding 模型"""
        if cls._embeddings is not None:
            return cls._embeddings

        # 确保模型缓存目录存在
        cls.MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # 获取配置
        model_name = "m3e-base"  # 默认值
        if db:
            config = db.query(EmbeddingConfig).filter(EmbeddingConfig.is_active == True).first()
            if config:
                model_name = config.model_name

        # 使用 HuggingFace 模型，指定缓存目录
        # 支持 m3e-base 等中文模型
        cls._embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            cache_folder=str(cls.MODEL_CACHE_DIR),  # 模型下载到项目目录
            model_kwargs={'device': 'cpu'},  # CPU 模式，如需 GPU 改为 'cuda'
            encode_kwargs={'normalize_embeddings': True}
        )

        return cls._embeddings

    @classmethod
    def get_vectorstore(cls, db: Session = None) -> Chroma:
        """获取向量存储"""
        if cls._vectorstore is not None:
            return cls._vectorstore

        # 确保目录存在
        persist_dir = os.path.join(settings.DATA_DIR, "rag_index")
        os.makedirs(persist_dir, exist_ok=True)

        embeddings = cls.get_embeddings(db)

        # 创建或加载向量库
        cls._vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings,
            collection_name="legal_documents"
        )

        return cls._vectorstore

    @classmethod
    def get_text_splitter(cls, db: Session = None) -> RecursiveCharacterTextSplitter:
        """获取文本分割器"""
        chunk_size = 512
        chunk_overlap = 50

        if db:
            config = db.query(EmbeddingConfig).filter(EmbeddingConfig.is_active == True).first()
            if config:
                chunk_size = config.chunk_size
                chunk_overlap = config.chunk_overlap

        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""]
        )

    @classmethod
    async def add_documents(
        cls,
        documents: List[Document],
        db: Session = None,
        metadatas: List[Dict[str, Any]] = None
    ) -> int:
        """
        添加文档到向量库

        Args:
            documents: 文档列表
            db: 数据库会话
            metadatas: 元数据列表

        Returns:
            添加的文档块数量
        """
        vectorstore = cls.get_vectorstore(db)
        text_splitter = cls.get_text_splitter(db)

        # 分割文档
        all_chunks = []
        for i, doc in enumerate(documents):
            chunks = text_splitter.split_documents([doc])
            # 添加元数据
            if metadatas and i < len(metadatas):
                for chunk in chunks:
                    chunk.metadata.update(metadatas[i])
            all_chunks.extend(chunks)

        # 添加到向量库
        if all_chunks:
            vectorstore.add_documents(all_chunks)
            # 持久化
            vectorstore.persist()

        return len(all_chunks)

    @classmethod
    async def add_text(
        cls,
        text: str,
        metadata: Dict[str, Any] = None,
        db: Session = None
    ) -> int:
        """
        添加文本到向量库

        Args:
            text: 文本内容
            metadata: 元数据
            db: 数据库会话

        Returns:
            添加的文档块数量
        """
        doc = Document(page_content=text, metadata=metadata or {})
        return await cls.add_documents([doc], db)

    @classmethod
    async def similarity_search(
        cls,
        query: str,
        k: int = 4,
        db: Session = None,
        filter: Dict[str, Any] = None
    ) -> List[Document]:
        """
        相似度搜索

        Args:
            query: 查询文本
            k: 返回结果数量
            db: 数据库会话
            filter: 元数据过滤条件

        Returns:
            相似文档列表
        """
        vectorstore = cls.get_vectorstore(db)

        if filter:
            results = vectorstore.similarity_search(
                query,
                k=k,
                filter=filter
            )
        else:
            results = vectorstore.similarity_search(query, k=k)

        return results

    @classmethod
    async def similarity_search_with_score(
        cls,
        query: str,
        k: int = 4,
        db: Session = None,
        filter: Dict[str, Any] = None
    ) -> List[tuple[Document, float]]:
        """
        相似度搜索（带分数）

        Args:
            query: 查询文本
            k: 返回结果数量
            db: 数据库会话
            filter: 元数据过滤条件

        Returns:
            (文档, 分数) 列表，分数越低越相似
        """
        vectorstore = cls.get_vectorstore(db)

        if filter:
            results = vectorstore.similarity_search_with_score(
                query,
                k=k,
                filter=filter
            )
        else:
            results = vectorstore.similarity_search_with_score(query, k=k)

        return results

    @classmethod
    async def delete_documents(cls, ids: List[str], db: Session = None) -> None:
        """
        删除文档

        Args:
            ids: 文档ID列表
            db: 数据库会话
        """
        vectorstore = cls.get_vectorstore(db)
        vectorstore._collection.delete(ids=ids)
        vectorstore.persist()

    @classmethod
    async def delete_by_metadata(cls, filter: Dict[str, Any], db: Session = None) -> None:
        """
        按元数据删除文档

        Args:
            filter: 元数据过滤条件
            db: 数据库会话
        """
        vectorstore = cls.get_vectorstore(db)
        # Chroma 的删除方式
        vectorstore._collection.delete(where=filter)
        vectorstore.persist()

    @classmethod
    async def get_retriever(cls, db: Session = None, search_kwargs: Dict = None):
        """
        获取检索器

        Args:
            db: 数据库会话
            search_kwargs: 搜索参数

        Returns:
            VectorStoreRetriever
        """
        vectorstore = cls.get_vectorstore(db)

        default_kwargs = {"k": 4}
        if search_kwargs:
            default_kwargs.update(search_kwargs)

        return vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs=default_kwargs
        )

    @classmethod
    def reset(cls):
        """重置服务实例（用于测试或配置更新）"""
        cls._embeddings = None
        cls._vectorstore = None
