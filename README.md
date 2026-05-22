# queue_system

Sistema de gestão de filas em Python, implementado conforme um diagrama de classes.

## Instalação

```bash
python -m pip install -r requirements.txt
```

## Execução HTTP

```bash
uvicorn queue_system.api:app --reload
```

A aplicação fica disponível em `http://127.0.0.1:8000`.

## Exemplo de uso

```py
from queue_system.gestor import GestorFila
from queue_system.entidades.pessoa import Pessoa

gestor = GestorFila(capacidade=100, politica='FIFO')
senha = gestor.emitir_senha(Pessoa(id=1, nome='Ana'))
print(gestor.posicao(senha.id))
```

## Estrutura do projeto

- `queue_system/gestor.py`: lógica principal da fila
- `queue_system/entidades/`: classes de domínio `Pessoa`, `Senha`, `Atendimento`
- `queue_system/operadores.py`: chamada e atendimento por operador
- `queue_system/painel.py`: consulta de posição e próxima senha
- `queue_system/monitor.py`: monitorização de filas por agência
- `queue_system/api.py`: API web com interface interativa
- `tests/`: testes unitários

## Diagrama de classes

O sistema segue o diagrama de classes fornecido e implementa as classes:
`GestorFila`, `Pessoa`, `Senha`, `Atendimento`, `Operador`, `PainelConsulta`, `MonitorAgencia`.
