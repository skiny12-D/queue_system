# queue_system

Sistema de gestão de filas em Python, implementado conforme um diagrama de classes.

## Instalação

```bash
python -m pip install -r requirements.txt
```

### Adicionar novos requerimentos

Se precisar de instalar dependências adicionais, use os comandos abaixo:

```bash
# instalar novas bibliotecas diretamente
python -m pip install qrcode Pillow twilio

# atualizar o ficheiro requirements.txt com todas as dependências atuais do ambiente
python -m pip freeze > requirements.txt
```

Se preferir adicionar uma biblioteca específica no `requirements.txt`, edite o ficheiro manualmente e inclua a nova dependência, por exemplo:

```text
requests>=2.30.0
```

## Execução HTTP

```bash
uvicorn queue_system.api:app --reload
```

A aplicação fica disponível em `http://127.0.0.1:8000`.

## Configuração de ambiente

Criar um ficheiro `.env` (não commitar) com as variáveis necessárias. Pode usar o ficheiro `.env.example` como referência.

Variáveis relevantes:

- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` — para envio de e-mail via SMTP.
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM` — para envio de SMS via Twilio.
- `ALERT_THRESHOLD` — posição na fila para disparar alerta (padrão `4`).
- `ALERT_CHECK_INTERVAL` — intervalo, em segundos, para verificação de proximidade (padrão `5`).

Exemplo rápido de execução com variáveis de ambiente:

```bash
# Unix/macOS
export SMTP_HOST=smtp.exemplo.com
export SMTP_PORT=587
export SMTP_USER=utilizador@exemplo.com
export SMTP_PASS=senha
export TWILIO_ACCOUNT_SID=ACxxxxx
export TWILIO_AUTH_TOKEN=xxxx
export TWILIO_FROM=+351912345678
uvicorn queue_system.api:app --reload

# Windows PowerShell
$env:SMTP_HOST = 'smtp.exemplo.com'
$env:SMTP_PORT = '587'
$env:SMTP_USER = 'utilizador@exemplo.com'
$env:SMTP_PASS = 'senha'
$env:TWILIO_ACCOUNT_SID = 'ACxxxxx'
$env:TWILIO_AUTH_TOKEN = 'xxxx'
$env:TWILIO_FROM = '+351912345678'
uvicorn queue_system.api:app --reload
```

## Notas de segurança

- Não commitar o ficheiro `.env`. Use `.env.example` como modelo.
- As credenciais do Twilio e do SMTP são sensíveis; trate-as com cuidado.

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
