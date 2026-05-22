# Design do queue_system

## Objetivo

Criar um sistema de gestão de filas com suporte a políticas de enfileiramento, monitorização online e interface HTTP.

## Decisões de design

- `GestorFila` administra o fluxo de senhas e aplica políticas de fila: `FIFO`, `LIFO` e `PRIORIDADE`.
- `Pessoa` representa o cliente e permite atribuir prioridade opcional.
- `Senha` regista o estado e os timestamps relevantes.
- `Atendimento` liga uma `Senha` a um `Operador` e regista início/fim.
- `Operador` usa o `GestorFila` para chamar clientes e gerir atendimentos.
- `PainelConsulta` expõe operações de leitura seguras para consultar posição e próxima senha.
- `MonitorAgencia` computa estado por agência, quantidade de pessoas e velocidade média.
- Persistência opcional em JSON mantém a fila entre reinícios.

## Diagrama de classes (ASCII)

```
Pessoa(id, nome, contacto, prioridade)
    |
    +-- Senha(id, hora_emissao, estado, pessoa)

GestorFila(capacidade, politica, fila)
    + emitir_senha(pessoa)
    + chamar_proximo()
    + posicao(senha_id)
    + cancelar_senha(senha_id)
    + listar_fila()

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
    + consultar_fila()
    + avaliar_velocidade()
```

## Concorrência

- Uso de `threading.Lock` em `GestorFila` para operações de emissão, chamada e cancelamento.
- Permite múltiplos operadores a acederem à mesma fila com segurança.

## Persistência

- Implementada como opção de arquivo JSON em `GestorFila`.
- Quando ativada, a fila é gravada após modificações e recarregada ao iniciar.

## Monitorização

- Velocidade da fila é calculada a partir dos atendimentos concluídos.
- Classificação: `rápida`, `média`, `lenta`.
- Endpoints públicos permitem consulta em tempo real.
