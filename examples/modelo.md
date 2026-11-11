---
titulo: Arquivo Modelo — Exemplo Completo de Documentação de Comandos
data: 2026-10-19
tags: [modelo, template, exemplo]
status: ativo
autor: Lavinia
---

# Nome do Serviço ou Sistema

Breve descrição geral do que é este serviço/sistema e onde está rodando.

## Configuração Inicial

```bash
# Comando para setup inicial
configurar_sistema   # label opcional — se aplica aos comandos seguintes, sem comentário inline

# Verificar status após instalação
status               # comentário explicativo opcional
```

---

## Operação Rotineira

Comandos usados na rotina de dia a dia da operação do serviço.

### Status e Monitoramento

```bash
# Lista o status geral do serviço (ativa/inativo/parado)
ver_status           # verificar se está rodando normalmente

# Logs recentes para depuração
logs -t              # tail logs em tempo real
logs --level=debug   # ver apenas mensagens de debug
```

---

### Controle Básico

```bash
# Iniciar serviço manualmente (se não estiver no supervisor)
iniciar              # trazer serviço pra frente sem recarregar tudo

# Parar serviço de forma controlada
parar                # para o processo com сигнал SIGTERM primeiro

# Reiniciar completamente
reiniciar            # stop + start em sequência
```

---

## Gerenciamento de Recursos

Comandos relacionados a uso de disco, memória e recursos do sistema.

### Disco e Armazenamento

```bash
# Verificar espaço disponível
especo --humano     # mostra em GB/MB formatados

# Limpar logs antigos
limpar_logs -a      # remove arquivos .old, .gz com mais de 7 dias
```

---

## Diagnóstico e Solução de Problemas

### Network

```bash
# Teste de conectividade básica
ping -c4 alvo        # testa ICMP para IP ou domínio

# Traceroute para identificar bloqueios na rota
traceroute destino   # mapeia saltos até o host de destino

# DNS — resolver e verificar resolvência
dig exemplo.com @resolver8_8_8_8  # consulta específica ao nome servidor
```

---

### Processos e Threads

```bash
# Listar processos do serviço relacionados
ps aux | grep servico  # filtra pelo nome no comando completo

# Identificar threads travadas/lock
top -H -p PID_PROCESSO   # detalha threads por processo específico

# Sinais para controle granular
kill -15 PID           # SIGTERM — parada limpa
kill -9 PID            # SIGKILL — força kill sem aviso prévio
```

---

## Scripts de Manutenção Automática

### Backup e Restauração

```bash
# Realizar backup pontual completo de dados
backup --destino=/backup/local --compressao=zstd

# Agendar snapshot com cron (via systemd timer)
systemctl enable backup-servico.timer
systemctl start backup-servico.timer

# Ver histórico de backups recentes
ls -lt /backup/local/servico/*/
```

---

## Comandos Especiais e Ajustes Avançados

### Reconfiguração

```bash
# Aplicar nova configuração (regras, políticas)
cargar_config config.yml          # substitui config atual no lugar
validar_config --estricto         # verifica sintaxe antes de aplicar

# Reiciar serviços dependentes após mudança de config
reiniciar_dependentes             # lista e restarta em cascata se necessário
```

---

### Limpeza e Otimização

```bash
# Limpeza completa de cache, temp, sessões antigas
manutencao_limpeza --completo     # remove /tmp/*, .cache/*, sessions expiradas

# Otimizar banco de dados interno se houver db_interno.db
otimizar_db   # VACUUM + ANALYZE + reindexação se necessário
```

---

## Troubleshooting Comum

Se aparecer algum destes erros/sintomas, testar os comandos abaixo:

### Serviço não inicia

```bash
# Ver logs do último startup
journalctl -u servico.service --no-pager -n 50 -r   # últimos 50 linhas em reverse

# Teste manual de startup com verificação de erros
inicar_seco --dry-run --debug               # modo seco sem aplicar mudanças reais
```

---

### Portas bloqueadas/ouvindo errado

```bash
ss -tlnp | grep portaNumerica      # lista sockets localmente bound
netstat -tlenp 2>/dev/null | grep servico   # alternativa em sistemas sem ss
```

---

## Notas Adicionais

- Este arquivo serve como **modelo completo** para documentar comandos de apps do Index
- Seguir formato: `## Seção` (fora de bloco) + comandos dentro de ```bash
- Usar labels (`# label`) antes de grupo de comando que se aplica a todos eles
- Comentários inline com `  # comentário` (2+ espaços) são **obrigatórios** para indexação correta
- Arquivo deve conter mínimo 3 setores distintos: configuração, operação, diagnóstico
- Se o serviço usa API REST em paralelo, incluir também seção de "API & Integrações"

---

*Mantido por Lavinia | Template v1.0*