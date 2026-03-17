# -*- coding: utf-8 -*-
"""
ErrorHandler - Módulo de Tratamento de Erros
Gerencia erros específicos com mensagens detalhadas
"""

import logging
from datetime import datetime


class ErrorHandler:
    """Classe para tratamento de erros"""

    def __init__(self):
        """Inicializa o handler de erros"""
        self.error_types = {
            'INIT_ERROR': {
                'prefix': '[INI]',
                'default_message': 'Erro de inicialização',
                'suggestion': 'Verifique se todos os módulos foram carregados corretamente'
            },
            'CONFIG_ERROR': {
                'prefix': '[CFG]',
                'default_message': 'Erro de configuração',
                'suggestion': 'Verifique as configurações na aba Configurações'
            },
            'NAVIGATION_ERROR': {
                'prefix': '[NAV]',
                'default_message': 'Erro de navegação',
                'suggestion': 'Verifique sua conexão com a internet e a URL'
            },
            'AUTH_ERROR': {
                'prefix': '[AUTH]',
                'default_message': 'Erro de autenticação',
                'suggestion': 'Verifique usuário e senha nas configurações'
            },
            'ELEMENT_NOT_FOUND': {
                'prefix': '[ELE]',
                'default_message': 'Elemento não encontrado',
                'suggestion': 'A estrutura da página pode ter mudado. Verifique os seletores.'
            },
            'PROCESS_ROW_ERROR': {
                'prefix': '[PRO]',
                'default_message': 'Erro ao processar registro',
                'suggestion': 'Verifique se os dados da planilha estão corretos'
            },
            'EXCEL_ERROR': {
                'prefix': '[XLS]',
                'default_message': 'Erro ao processar planilha',
                'suggestion': 'Verifique se o arquivo está no formato correto e não está corrompido'
            },
            'AUTOMATION_ERROR': {
                'prefix': '[AUTO]',
                'default_message': 'Erro na automação',
                'suggestion': 'Tente reiniciar o processo ou verificar os logs para mais detalhes'
            },
            'TIMEOUT_ERROR': {
                'prefix': '[TIM]',
                'default_message': 'Timeout',
                'suggestion': 'A operação demorou mais que o esperado. Tente aumentar o timeout.'
            },
            'UNKNOWN_ERROR': {
                'prefix': '[UNK]',
                'default_message': 'Erro desconhecido',
                'suggestion': 'Contate o suporte com os logs do erro'
            }
        }

    def handle(self, error_type, error, context=''):
        """
        Trata um erro e retorna mensagem formatada

        Args:
            error_type: Tipo do erro
            error: Erro original
            context: Contexto do erro

        Returns:
            Mensagem formatada do erro
        """
        error_config = self.error_types.get(error_type, self.error_types['UNKNOWN_ERROR'])

        error_message = {
            'type': error_type,
            'prefix': error_config['prefix'],
            'message': error_config['default_message'],
            'context': context,
            'original_error': str(error) if error else 'Erro desconhecido',
            'suggestion': error_config['suggestion'],
            'timestamp': self._get_timestamp()
        }

        # Log detalhado do erro
        self._log_detailed_error(error_message)

        return self._format_error_message(error_message)

    def _log_detailed_error(self, error_message):
        """Log detalhado do erro no console"""
        logger = logging.getLogger('ErrorHandler')

        logger.error("=" * 50)
        logger.error(f"ERRO {error_message['prefix']}: {error_message['type']}")
        logger.error(f"  Mensagem: {error_message['message']}")
        logger.error(f"  Contexto: {error_message['context']}")
        logger.error(f"  Erro Original: {error_message['original_error']}")
        logger.error(f"  Sugestão: {error_message['suggestion']}")
        logger.error(f"  Timestamp: {error_message['timestamp']}")
        logger.error("=" * 50)

    def _format_error_message(self, error_message):
        """Formata mensagem de erro para display"""
        parts = [
            f"{error_message['prefix']} {error_message['message']}",
            f"Contexto: {error_message['context']}",
            f"Erro: {error_message['original_error']}",
            f"Sugestão: {error_message['suggestion']}"
        ]

        return ' | '.join([p for p in parts if p])

    def _get_timestamp(self):
        """Obtém timestamp atual"""
        return datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    def create_error(self, message, error_type='UNKNOWN_ERROR', suggestion=''):
        """
        Cria erro personalizado

        Args:
            message: Mensagem do erro
            error_type: Tipo do erro
            suggestion: Sugestão de solução

        Returns:
            Dicionário com informações do erro
        """
        return {
            'type': error_type,
            'message': message,
            'suggestion': suggestion,
            'timestamp': self._get_timestamp()
        }

    def handle_element_not_found(self, selector, context):
        """
        Trata erro de elemento não encontrado

        Args:
            selector: Seletor do elemento
            context: Contexto do erro

        Returns:
            Mensagem de erro formatada
        """
        return self.handle(
            'ELEMENT_NOT_FOUND',
            f"Selector: {selector}",
            context
        )

    def handle_timeout(self, operation, timeout):
        """
        Trata erro de timeout

        Args:
            operation: Nome da operação
            timeout: Timeout em ms

        Returns:
            Mensagem de erro formatada
        """
        return self.handle(
            'TIMEOUT_ERROR',
            f"Operação: {operation}, Timeout: {timeout}ms",
            f"Timeout em {operation}"
        )

    def handle_auth_error(self, message):
        """
        Trata erro de autenticação

        Args:
            message: Mensagem adicional

        Returns:
            Mensagem de erro formatada
        """
        return self.handle(
            'AUTH_ERROR',
            message,
            'Falha no login'
        )

    def handle_navigation_error(self, url, error):
        """
        Trata erro de navegação

        Args:
            url: URL acessada
            error: Erro original

        Returns:
            Mensagem de erro formatada
        """
        return self.handle(
            'NAVIGATION_ERROR',
            error,
            f"Navegando para: {url}"
        )

    def handle_process_row_error(self, row_index, error):
        """
        Trata erro de processamento de linha

        Args:
            row_index: Índice da linha
            error: Erro original

        Returns:
            Mensagem de erro formatada
        """
        return self.handle(
            'PROCESS_ROW_ERROR',
            error,
            f"Processando linha {row_index + 1}"
        )

    def is_recoverable_error(self, error):
        """
        Verifica se é erro recuperável

        Args:
            error: Erro a ser verificado

        Returns:
            True se for recuperável, False caso contrário
        """
        error_str = str(error).lower()

        recoverable_keywords = [
            'timeout', 'network', 'connection', 'reset',
            'timed out', 'socket hang up', 'econnreset'
        ]

        return any(keyword in error_str for keyword in recoverable_keywords)

    def get_friendly_message(self, error):
        """
        Obtém mensagem de erro amigável

        Args:
            error: Erro original

        Returns:
            Mensagem amigável
        """
        error_str = str(error).lower()

        if 'authentication' in error_str or 'login' in error_str:
            return 'Falha no login. Verifique usuário e senha.'

        if 'timeout' in error_str:
            return 'A operação demorou muito. Tente novamente.'

        if 'not found' in error_str or 'element' in error_str:
            return 'Elemento não encontrado na página. A estrutura pode ter mudado.'

        if 'network' in error_str:
            return 'Problema de conexão. Verifique sua internet.'

        return f"Ocorreu um erro: {str(error)[:100]}..."

    def format_traceback(self, tb_string):
        """
        Formata traceback para display

        Args:
            tb_string: String do traceback

        Returns:
            Traceback formatado
        """
        if not tb_string:
            return ''

        lines = tb_string.strip().split('\n')

        # Mostrar apenas as últimas 10 linhas
        if len(lines) > 10:
            lines = ['...'] + lines[-10:]

        return '\n'.join(lines)
