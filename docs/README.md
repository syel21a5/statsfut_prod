# 📚 Documentação do Projeto StatsFut

Esta pasta contém toda a documentação técnica do sistema de atualização automática de partidas.

## 📄 Arquivos

### [walkthrough.md](walkthrough.md)
Guia completo do sistema inteligente de polling implementado, incluindo:
- O que mudou no sistema
- Arquivos modificados
- Como fazer deploy no servidor
- Como monitorar o serviço
- Benefícios da otimização

### [implementation_plan.md](implementation_plan.md)
Plano técnico detalhado da otimização, incluindo:
- Análise do problema
- Estratégia de solução
- Intervalos de polling otimizados
- Estimativa de consumo de API

### [deploy_commands.md](deploy_commands.md)
Referência rápida com todos os comandos necessários para:
- Atualizar código no servidor
- Instalar o serviço systemd
- Monitorar logs
- Gerenciar o serviço

## 🎯 Sistema Implementado

**Polling Inteligente de APIs**
- Modo ECONÔMICO: 5 minutos (sem jogos)
- Modo ATIVO: 1 minuto (com jogos)
- Economia: ~80% de chamadas API
- Consumo: ~960 requests/dia (de 8.200 disponíveis)
