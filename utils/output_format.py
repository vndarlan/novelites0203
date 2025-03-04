from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OutputFormatManager:
    """
    Gerenciador de formatos de saída personalizados.
    
    Esta classe permite definir e validar formatos de saída estruturados
    para as tarefas do agente.
    """
    def __init__(self):
        self.formats = {}
    
    def register_format(self, name: str, model: type):
        """
        Registra um formato de saída.
        
        Args:
            name: Nome do formato
            model: Classe Pydantic que define o formato
        """
        if not issubclass(model, BaseModel):
            raise TypeError("O modelo deve ser uma subclasse de BaseModel")
        
        self.formats[name] = model
        logger.info(f"Formato de saída '{name}' registrado com sucesso")
    
    def get_format(self, name: str) -> Optional[type]:
        """
        Obtém um formato de saída pelo nome.
        
        Args:
            name: Nome do formato
            
        Returns:
            Classe Pydantic ou None se não encontrado
        """
        return self.formats.get(name)
    
    def get_format_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Obtém o esquema JSON de um formato de saída.
        
        Args:
            name: Nome do formato
            
        Returns:
            Esquema JSON ou None se não encontrado
        """
        format_model = self.get_format(name)
        if format_model:
            return format_model.schema()
        return None
    
    def validate_output(self, name: str, output_data: Dict[str, Any]) -> Optional[BaseModel]:
        """
        Valida dados de saída de acordo com um formato.
        
        Args:
            name: Nome do formato
            output_data: Dados a serem validados
            
        Returns:
            Instância validada do modelo ou None se inválido
        """
        format_model = self.get_format(name)
        if not format_model:
            logger.warning(f"Formato '{name}' não encontrado")
            return None
        
        try:
            # Tentar converter string JSON para dict se necessário
            if isinstance(output_data, str):
                try:
                    output_data = json.loads(output_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao converter string JSON: {e}")
                    return None
            
            # Validar usando o modelo
            validated = format_model(**output_data)
            return validated
        
        except Exception as e:
            logger.error(f"Erro ao validar saída com formato '{name}': {e}")
            return None
    
    def format_to_prompt(self, name: str) -> str:
        """
        Gera um exemplo de prompt para o formato especificado.
        
        Args:
            name: Nome do formato
            
        Returns:
            String com exemplo de formato para incluir no prompt
        """
        format_model = self.get_format(name)
        if not format_model:
            return ""
        
        schema = format_model.schema()
        example = {}
        
        # Gerar exemplo com base nas propriedades
        for prop_name, prop in schema.get('properties', {}).items():
            if prop.get('type') == 'string':
                example[prop_name] = f"exemplo de {prop_name}"
            elif prop.get('type') == 'integer':
                example[prop_name] = 42
            elif prop.get('type') == 'number':
                example[prop_name] = 3.14
            elif prop.get('type') == 'boolean':
                example[prop_name] = True
            elif prop.get('type') == 'array':
                example[prop_name] = []
            elif prop.get('type') == 'object':
                example[prop_name] = {}
        
        # Formatar como JSON
        return f"""Formato de saída esperado:
```json
{json.dumps(example, indent=2)}
```
Por favor, retorne o resultado final neste formato JSON."""

# Exemplos de modelos de saída predefinidos

class ProductInfo(BaseModel):
    """Informações de um produto"""
    name: str = Field(..., description="Nome do produto")
    price: float = Field(..., description="Preço do produto")
    available: bool = Field(..., description="Disponibilidade do produto")
    description: Optional[str] = Field(None, description="Descrição do produto")
    rating: Optional[float] = Field(None, description="Classificação do produto (0-5)")
    reviews_count: Optional[int] = Field(None, description="Número de avaliações")

class Products(BaseModel):
    """Lista de produtos"""
    products: List[ProductInfo] = Field(..., description="Lista de produtos encontrados")
    source_url: str = Field(..., description="URL da página de origem")
    search_query: Optional[str] = Field(None, description="Termo de pesquisa utilizado")

class NewsArticle(BaseModel):
    """Informações de um artigo de notícia"""
    title: str = Field(..., description="Título do artigo")
    source: str = Field(..., description="Fonte da notícia")
    date_published: str = Field(..., description="Data de publicação")
    summary: str = Field(..., description="Resumo ou trecho do artigo")
    url: str = Field(..., description="URL do artigo")

class NewsDigest(BaseModel):
    """Resumo de notícias"""
    articles: List[NewsArticle] = Field(..., description="Lista de artigos de notícias")
    topic: Optional[str] = Field(None, description="Tópico ou categoria das notícias")
    source_url: str = Field(..., description="URL da página de origem")

# Criar instância do gerenciador e registrar formatos pré-definidos
output_format_manager = OutputFormatManager()
output_format_manager.register_format("produtos", Products)
output_format_manager.register_format("noticias", NewsDigest)