# Design do queue_system

## Objetivo

Criar um sistema de gestão de filas com suporte a políticas de enfileiramento, notificações digitais, geração de QR codes, monitorização online e interface HTTP.

## Decisões de design

- `GestorFila` administra o fluxo de senhas e aplica políticas de fila: `FIFO`, `LIFO` e `PRIORIDADE`.
- `Pessoa` representa o cliente e guarda atributos de prioridade, contato e acesso digital.
- `Senha` regista o estado, timestamps, via de emissão, payload do QR e o QR Base64.
- `Atendimento` liga uma `Senha` a um `Operador` e regista início/fim.
- `Operador` usa o `GestorFila` para chamar clientes e gerir atendimentos.
- `PainelConsulta` expõe operações de leitura seguras para consultar posição e próxima senha.
- `MonitorAgencia` computa estado por agência, quantidade de pessoas e velocidade média.
- `Notificador` abstrai envios de e-mail e SMS, com fallback para logging quando não existem credenciais.
- `api.py` expõe endpoints para emissão, consulta, cancelamento, QR code, alertas e monitorização.
- A persistência em JSON mantém o estado da fila entre reinícios.
- A inicialização do serviço usa `FastAPI` `lifespan` para disparar o watcher de proximidade e enviar alertas de fila.

## Diagrama de classes (ASCII)

```
Pessoa(id, nome, contacto, email, telefone, prioridade, acesso_digital)
    |
    +-- Senha(id, hora_emissao, estado, via_emissao, qr_payload, qr_code_base64, alerta_enviado, pessoa)

GestorFila(capacidade, politica, fila, persistencia)
    + emitir_senha(pessoa)
    + chamar_proximo()
    + posicao(senha_id)
    + cancelar_senha(senha_id)
    + listar_fila()
    + obter_senha(senha_id)
    + register_notification_contact(senha_id, contact_info)

Notificador()
    + enviar_email(destino, assunto, mensagem)
    + enviar_sms(telefone, mensagem)
    + notificar_usuario(email, telefone, mensagem)

Operador(id, nome)
    + chamar(gestor)
    + iniciar_atendimento(senha)
    + terminar_atendimento(atendimento)

Atendimento(id, senha, operador, inicio, fim)
    + iniciar()
    + terminar()

PainelConsulta(gestor)
    + consultar_posicao(senha_id)
    + proxima_senha()

MonitorAgencia(agencia, gestor)
    + listar_agencias()
    + estado_agencia()
    + avaliar_velocidade()

API FastAPI
    + GET /
    + POST /fila/emitir
    + GET /fila/qr/{senha_id}
    + GET /fila/alerta/{senha_id}
    + POST /fila/chamar
    + GET /fila/posicao/{senha_id}
    + POST /fila/cancelar/{senha_id}
    + GET /fila/listar
    + GET /monitor/agencias
    + GET /monitor/agencias/{agencia}
    + GET /monitor/velocidade
```

## Funcionalidades atualizadas

- Geração de QR codes para senhas digitais.
- Armazenamento temporário de contatos para alertas por e-mail e SMS sem persistir esses dados em JSON.
- Alertas de proximidade disparados quando uma senha digital fica próxima do atendimento.
- Endpoints dedicados para obter o QR code e verificar se deve ser exibido alerta.
- Interação frontal via HTML/JavaScript para emitir senhas, consultar posição, ver QR e monitorizar a agência.
- Uso de `FastAPI` `lifespan` em vez de `@app.on_event("startup")` para inicializar o watcher.

## Concorrência

- O `GestorFila` usa travamentos (`threading.Lock`) para proteger as operações mutáveis da fila.
- O watcher de proximidade roda em thread separada como daemon, permitindo notificações contínuas enquanto o servidor está ativo.

## Persistência

- O estado da fila é gravado em `queue_state.json` após alterações.
- O JSON persiste a lista de senhas e o estado geral, mas não guarda contatos temporários de notificações.

## Monitorização

- A velocidade da fila é estimada a partir dos atendimentos concluídos.
- A API expõe métricas de agência e velocidade para consultas em tempo real.
- O painel de interface web permite ver o estado da agência e listar a fila atual.
