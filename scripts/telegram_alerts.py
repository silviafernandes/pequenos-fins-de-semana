"""Telegram delivery checks. Credentials stay in environment variables, never logs."""
import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
import requests

TEST_MESSAGE=('🧪 TESTE — Pequenos fins de semana\n\n'
              'Mensagem de teste da agenda. Se a consegues ler, o bot chegou a esta conversa.\n\n'
              'Agenda: https://silviafernandes.github.io/pequenos-fins-de-semana/')

@dataclass(frozen=True)
class Result:
    status: str
    reason: str
    missing: tuple = ()

    @property
    def accepted(self):return self.status=='accepted'


def configuration(environ=None):
    environ=os.environ if environ is None else environ
    token=environ.get('TELEGRAM_BOT_TOKEN','').strip()
    chat=environ.get('TELEGRAM_CHAT_ID','').strip()
    missing=tuple(name for name,value in [('TELEGRAM_BOT_TOKEN',token),('TELEGRAM_CHAT_ID',chat)] if not value)
    if missing:return token,chat,Result('not-configured','Faltam secrets no GitHub Actions: '+', '.join(missing),missing)
    if not re.fullmatch(r'\d+:[A-Za-z0-9_-]+',token):return token,chat,Result('invalid-config','Formato de TELEGRAM_BOT_TOKEN inválido; volta a definir o secret.')
    if not re.fullmatch(r'-?\d+|@[A-Za-z][A-Za-z0-9_]{4,31}',chat):return token,chat,Result('invalid-config','Formato de TELEGRAM_CHAT_ID inválido; volta a definir o secret.')
    return token,chat,Result('ready','Credenciais presentes. A entrega ainda precisa do teste de envio.')


def trim_message(text):
    # Telegram measures its text limit in UTF-16 code units.
    return text.encode('utf-16-le')[:8000].decode('utf-16-le',errors='ignore')


def send_message(text,session=None,environ=None):
    token,chat,setup=configuration(environ)
    if setup.status!='ready':return setup
    if not isinstance(text,str) or not text.strip():return Result('skipped','Nenhuma mensagem para enviar.')
    client=session or requests.Session()
    try:
        response=client.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':trim_message(text),'disable_web_page_preview':True},timeout=10,allow_redirects=False)
    except requests.RequestException:
        return Result('uncertain','Sem confirmação do Telegram por falha de ligação. Não repetimos o envio automaticamente para evitar duplicados.')
    if 300<=response.status_code<400:return Result('failed','O Telegram devolveu um redirecionamento; o pedido não foi seguido.')
    try:data=response.json()
    except (ValueError,TypeError):return Result('uncertain','A resposta do Telegram não pôde ser validada. Não repetimos o envio automaticamente.')
    if not isinstance(data,dict):return Result('uncertain','Resposta do Telegram inesperada; entrega sem confirmação.')
    if response.status_code==200 and data.get('ok') is True:
        message=data.get('result')
        if not isinstance(message,dict) or type(message.get('message_id')) is not int or message['message_id']<=0:return Result('uncertain','O Telegram não devolveu uma confirmação de mensagem válida.')
        destination=message.get('chat')
        matches=isinstance(destination,dict) and ((str(destination.get('id'))==str(int(chat))) if re.fullmatch(r'-?\d+',chat) else str(destination.get('username','')).casefold()==chat[1:].casefold())
        if not matches:return Result('uncertain','O destino da confirmação não corresponde à conversa configurada.')
        return Result('accepted','O Telegram aceitou a mensagem para a conversa configurada. Isto não confirma leitura no telemóvel.')
    code=data.get('error_code',response.status_code)
    if type(code) is not int:code=response.status_code
    reasons={401:'Token recusado pelo Telegram. Atualiza TELEGRAM_BOT_TOKEN.',403:'O bot não pode enviar para esta conversa. Confirma que está iniciado e desbloqueado.',429:'Limite de envios do Telegram atingido. Aguarda antes de executar outro teste.'}
    if code==400:return Result('failed','Conversa ou pedido recusado. Abre o bot, envia /start e confirma TELEGRAM_CHAT_ID.')
    if code in reasons:return Result('failed',reasons[code])
    if response.status_code>=500:return Result('uncertain','Erro do serviço Telegram; entrega sem confirmação e sem repetição automática.')
    return Result('failed','O Telegram não confirmou a entrega. Consulta a configuração e volta a testar.')


def send_alerts(lines,session=None,environ=None):
    lines=[line for line in lines if isinstance(line,str) and line.strip()]
    if not lines:return Result('skipped','Nenhum alerta novo para enviar.')
    environ=os.environ if environ is None else environ
    if environ.get('GITHUB_EVENT_NAME')=='push':return Result('disabled','Envio desativado para publicações de código.')
    text='✳ Novidades — Pequenos fins de semana\n\n'+'\n\n'.join(lines[:8])+'\n\nConfirmar sempre a inscrição na origem.'
    return send_message(text,session,environ)


def report(result,summary_path=None):
    # Only fixed status/reason strings and secret NAMES are printed, never API bodies.
    text=f'Telegram: {result.status} — {result.reason}'
    print(text)
    path=summary_path or os.environ.get('GITHUB_STEP_SUMMARY')
    if path:
        with Path(path).open('a',encoding='utf-8') as output:output.write('\n### Telegram\n\n'+text+'\n')


def main(argv=None):
    parser=argparse.ArgumentParser(description='Verificar configuração ou enviar uma única mensagem de teste Telegram.')
    parser.add_argument('--send-test',action='store_true',help='Enviar uma mensagem identificada como TESTE para a conversa configurada.')
    args=parser.parse_args(argv)
    result=send_message(TEST_MESSAGE) if args.send_test else configuration()[2]
    report(result)
    return 0 if result.status in ('ready','accepted') else 1

if __name__=='__main__':raise SystemExit(main())
