import streamlit as st

def show_help_page():
    """Mostra a página de ajuda e documentação"""
    st.title("📚 Ajuda e Documentação")
    
    # Visão geral
    st.markdown("""
    ## Visão Geral
    
    O **Gerenciador de Agentes IA** é uma plataforma para criar e gerenciar agentes de IA que podem 
    navegar e interagir com sites da web de forma autônoma. Usando modelos avançados de linguagem 
    (LLMs), os agentes podem entender instruções em linguagem natural e executar tarefas complexas.
    """)
    
    # Começando
    with st.expander("🚀 Começando"):
        st.markdown("""
        ### Primeiros Passos
        
        1. **Configure as APIs**: Na aba "Configuração", adicione pelo menos uma chave de API para um provedor de LLM.
        2. **Crie uma Tarefa**: Na aba "Criar Tarefa", escreva instruções detalhadas para o agente e selecione o modelo LLM.
        3. **Execute a Tarefa**: Clique em "Iniciar Tarefa" e observe o agente executar as instruções.
        4. **Analise os Resultados**: Veja os passos executados, capturas de tela e resultado final na página de detalhes da tarefa.
        
        ### Dicas para Boas Instruções
        
        - Seja específico e forneça URLs completas
        - Descreva cada etapa que deseja que o agente execute
        - Inclua critérios claros para o agente saber quando a tarefa está concluída
        - Para tarefas complexas, divida em subtarefas mais simples
        """)
    
    # Modelos suportados
    with st.expander("🧠 Modelos Suportados"):
        st.markdown("""
        ### Provedores de LLM Suportados
        
        | Provedor | Modelos Recomendados | Características |
        |----------|----------------------|-----------------|
        | OpenAI | GPT-4o | Melhor desempenho geral, recomendado para maioria das tarefas |
        | Anthropic | Claude 3.5 Sonnet | Excelente compreensão e seguimento de instruções |
        | Azure OpenAI | GPT-4 | Bom para empresas com requisitos de conformidade |
        | Google Gemini | Gemini-1.5 Pro | Gratuito para testes, bom desempenho |
        | DeepSeek | DeepSeek-V3 | 30x mais barato que GPT-4o, bom custo-benefício |
        | Ollama | Llama3, Mistral | Modelos locais, sem custo, mas desempenho limitado |
        
        ### Recomendações de Modelo por Tipo de Tarefa
        
        - **Tarefas de Navegação Complexa**: GPT-4o, Claude 3.5 Sonnet
        - **Extração de Dados Estruturados**: GPT-4o, DeepSeek-V3
        - **Tarefas Simples/Repetitivas**: Gemini, GPT-3.5 Turbo
        - **Ambiente Local/Offline**: Ollama com Llama3
        """)
    
    # Recursos avançados
    with st.expander("🔧 Recursos Avançados"):
        st.markdown("""
        ### Configurações do Navegador
        
        - **Headless Mode**: Executar navegador invisível (mais eficiente) ou visível (para depuração)
        - **Dimensões da Janela**: Ajustar o tamanho da janela do navegador
        - **Tempos de Espera**: Configurar tempos de carregamento e espera por rede
        - **Chrome Real**: Conectar ao seu navegador Chrome existente com suas sessões já autenticadas
        
        ### Dados Sensíveis
        
        Utilize placeholders para senhas e informações confidenciais. Por exemplo:
        
        1. Adicione um placeholder como `x_password` na seção de Dados Sensíveis
        2. Use o placeholder em suas instruções: "Faça login usando x_password"
        3. O modelo nunca verá o valor real, apenas o placeholder
        
        ### Formatos de Saída Personalizados
        
        Defina estruturas JSON para os resultados, útil para integração com outros sistemas:
        
        ```json
        {
          "produto": {
            "nome": "Nome do produto",
            "preço": 99.99,
            "disponibilidade": true
          }
        }
        ```
        
        ### Ações Iniciais
        
        Configure ações para serem executadas automaticamente antes do agente começar a análise:
        - Abrir sites específicos
        - Preencher formulários de login
        - Navegar até uma seção específica de um site
        """)
    
    # Solução de problemas
    with st.expander("🔍 Solução de Problemas"):
        st.markdown("""
        ### Problemas Comuns
        
        **O agente não consegue interagir com um elemento**
        - Verifique se o seletor CSS está correto
        - Alguns sites têm proteções contra automação
        - Tente usar outro método para interagir (ex: JavaScript executado na página)
        
        **O agente está lento ou travando**
        - Limite o número máximo de passos nas configurações avançadas
        - Reduza os tempos de espera por carregamento
        - Verifique se o site tem muitos elementos interativos ou animações
        
        **O modelo não entende as instruções**
        - Seja mais específico e detalhado
        - Divida tarefas complexas em subtarefas menores
        - Use um modelo mais avançado (ex: GPT-4o em vez de GPT-3.5)
        
        **Erros de autenticação com APIs**
        - Verifique se as chaves API foram configuradas corretamente
        - Confirme que a chave tem saldo/créditos suficientes
        - Verifique limites de taxa da API
        """)
    
    # Exemplos de uso
    with st.expander("📋 Exemplos de Uso"):
        st.markdown("""
        ### Exemplos de Tarefas Bem-Sucedidas
        
        **Pesquisa de Produtos**
        ```
        Visite amazon.com, pesquise por "fones de ouvido bluetooth", classifique por classificação média e extraia informações dos 3 primeiros resultados.
        Para cada produto, capture o nome, preço, classificação e número de avaliações.
        ```
        
        **Monitoramento de Notícias**
        ```
        Visite news.google.com, navegue até a seção de tecnologia e extraia os títulos e resumos das 5 principais notícias.
        Para cada notícia, capture o título, fonte e hora da publicação.
        ```
        
        **Preenchimento de Formulário**
        ```
        Visite o site example.com/contact, preencha o formulário de contato com:
        - Nome: John Doe
        - Email: john.doe@example.com
        - Assunto: Solicitação de Informações
        - Mensagem: "Olá, gostaria de receber mais informações sobre seus serviços."
        Capture uma screenshot do formulário preenchido, mas NÃO envie o formulário.
        ```
        """)
    
    # Referências
    st.markdown("""
    ## Referências e Recursos Adicionais
    
    - [Documentação do Playwright Python](https://playwright.dev/python/)
    - [Documentação do Streamlit](https://docs.streamlit.io/)
    - [Guia de Automação Web com IA](https://browser-use.github.io/browser-use/)
    
    Para dúvidas ou suporte adicional, entre em contato com a equipe de desenvolvimento.
    """)
    
    # Botão para voltar
    if st.button("← Voltar ao Menu Principal"):
        st.experimental_rerun()

if __name__ == "__main__":
    st.set_page_config(
        page_title="Ajuda - Gerenciador de Agentes IA",
        page_icon="📚",
        layout="wide"
    )
    show_help_page()