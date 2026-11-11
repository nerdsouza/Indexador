---
titulo: Plano de Evolução e Arquitetura Dual — Indexador
data: 2026-11-10
tags: [indexador, arquitetura, planejamento, refatoracao, cli, web, docker, versionamento]
status: ativo
autor: NerdSouza
---

# Plano de Evolução e Arquitetura Dual — Indexador

Este documento consolida a visão de produto, a arquitetura dual de imagens Docker separadas, o script wrapper para o terminal, a estratégia de versionamento semântico e o planejamento em etapas incrementais.

---

## 1. Estratégia de Docker Dual (Web vs. CLI Leve)

Para atender ao desejo de ter duas formas limpas e independentes de consumo sem carregar peso desnecessário:

### 🐳 Imagem Web (`Dockerfile` ou `Dockerfile.web`)
- **Foco:** Servidor FastAPI + interface web estática.
- **Uso:** Subido via Docker Compose para acesso na LAN/celular.
- **Porta:** 8000 (vinculada a `127.0.0.1` ou proxy reverso).

### ⚡ Imagem CLI Leve (`Dockerfile.cli`)
- **Foco:** Container enxuto contendo apenas o Python e o script `busca_index.py` (e bibliotecas de suporte).
- **Abordagem do Wrapper / Alias (`buscador-cli`):**
  - O usuário cria um alias ou script wrapper no host (`buscador-cli`).
  - Ao chamar o comando, o script verifica se a imagem Docker do CLI existe localmente.
  - Se não existir, ele faz o build automático (ou pull).
  - Em seguida, executa o container em modo interativo (`-it`) com volume mount apontando para o vault do host (`Index/`), entregando o REPL do terminal instantaneamente.

---

## 2. Estratégia de Versionamento Semântico (`MAJOR.MINOR.PATCH`)

O versionamento do projeto será rigidamente controlado através do arquivo `VERSION` na raiz, facilitando rastreio e marcos entre sessões:
- **`X.0.0` (Major):** Mudanças estruturais grandes na arquitetura, quebra de compatibilidade ou reformulação completa das interfaces.
- **`0.X.0` (Minor):** Adição de novas funcionalidades significativas (ex: inclusão da Imagem CLI Docker, novo módulo de montagem web).
- **`0.0.X` (Patch):** Correções de bugs, ajustes de parsing, melhorias na busca ou refinamentos pontuais.

---

## 3. Fases de Implementação Incremental

O desenvolvimento ocorrerá em etapas úteis, testadas e versionadas:

- **Fase 3.1 (Versão `3.1.0` - Base & Biblioteca Compartilhada) — ✅ concluída em 2026-11-11:**
  - Isolar a lógica pura em `lib/indexador.py` e `lib/explicador.py`.
  - Corrigir os bugs críticos de parsing e exclusão de pastas ocultas/glossário.
- **Fase 3.2 (Versão `3.2.0` - Docker CLI Leve & Wrapper) — ✅ concluída em 2026-11-11:**
  - Criar o `Dockerfile.cli` otimizado para terminal.
  - Desenvolver o script wrapper / alias (`buscador-cli`) com auto-build e gerenciamento de volume.
- **Fase 3.3 (Versão `3.3.0` - Refinamento da Web & Docker Web):**
  - Estabilizar a API FastAPI (`main.py`) e a interface web.
  - Ajustar Docker Compose para o serviço web.
- **Fase 3.4 (Versão `3.4.0` - Futuro: Área de Montagem / Avançados):**
  - Implementar a área "Montar" e decomposição avançada de comandos.
