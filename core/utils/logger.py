# -*- coding: utf-8 -*-
"""
Logger - Sistema de Logs
Gerencia logs de acompanhamento da aplicação
"""

import logging
from datetime import datetime
from pathlib import Path
import time

try:
    from colorama import Fore, Back, Style, init
    HAS_COLORAMA = True
    init(autoreset=True)  # Auto-reset após cada print
except ImportError:
    HAS_COLORAMA = False
    # Fallback para ANSI codes
    class Fore:
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        CYAN = '\033[96m'
    class Style:
        RESET_ALL = '\033[0m'
        BRIGHT = '\033[1m'


class ColoredFormatter(logging.Formatter):
    """Formatter customizado com cores para os logs"""
    
    COLORS = {
        'INFO': '\033[94m',      # Azul
        'SUCCESS': '\033[92m',   # Verde
        'WARNING': '\033[93m',   # Amarelo
        'ERROR': '\033[91m',     # Vermelho
        'DEBUG': '\033[96m',     # Ciano
        'CRITICAL': '\033[91m'   # Vermelho
    }
    
    RESET = '\033[0m'
    BRIGHT = '\033[1m'
    
    def format(self, record):
        """Formata o registro com cores"""
        # Obter nível do log
        levelname = record.levelname
        
        # Mapeamento de SUCCESS para INFO (já que SUCCESS não é nível padrão)
        if levelname == 'INFO' and '✓' in record.getMessage():
            color = self.COLORS.get('SUCCESS', self.RESET)
        else:
            color = self.COLORS.get(levelname, self.RESET)
        
        # Criar registro customizado com cor
        record.levelname = f"{color}{self.BRIGHT}{levelname:7}{self.RESET}"
        record.asctime = f"{color}{self.format_time(record)}{self.RESET}"
        
        # Formatar mensagem com cor
        result = super().format(record)
        
        return result
    
    def format_time(self, record):
        """Formata o tempo"""
        ct = self.converter(record.created)
        if self.datefmt:
            s = time.strftime(self.datefmt, ct)
        else:
            s = time.strftime("%Y-%m-%d %H:%M:%S", ct)
        return s


class Logger:
    """Classe de Logger para a aplicação"""

    def __init__(self, log_file=None, console=True, level=logging.INFO):
        """
        Inicializa o logger

        Args:
            log_file: Caminho do arquivo de log (opcional)
            console: Se True, exibe logs no console
            level: Nível de log (padrão: INFO)
        """
        self.logs = []
        self.max_logs = 1000
        self.auto_scroll = True

        # Configurar logging
        self.logger = logging.getLogger('LogTudo')
        self.logger.setLevel(level)

        # Limpar handlers existentes
        self.logger.handlers = []

        # Handler de console com cores
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_formatter = ColoredFormatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        # Handler de arquivo (sem cores)
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def get_timestamp(self):
        """Obtém timestamp atual formatado"""
        return datetime.now().strftime('%H:%M:%S')

    def info(self, message, details=None):
        """Adiciona log de informação"""
        self.logger.info(message)
        self._add_to_memory('INFO', message, details)

    def success(self, message, details=None):
        """Adiciona log de sucesso"""
        self.logger.info(f"✓ {message}")
        self._add_to_memory('SUCCESS', message, details)

    def warning(self, message, details=None):
        """Adiciona log de aviso"""
        self.logger.warning(message)
        self._add_to_memory('WARNING', message, details)

    def error(self, message, details=None):
        """Adiciona log de erro"""
        self.logger.error(message)
        self._add_to_memory('ERROR', message, details)

    def debug(self, message, details=None):
        """Adiciona log de debug"""
        self.logger.debug(message)
        self._add_to_memory('DEBUG', message, details)

    def _add_to_memory(self, level, message, details):
        """Adiciona log à memória"""
        entry = {
            'timestamp': self.get_timestamp(),
            'level': level,
            'message': message,
            'details': details,
            'id': f"{datetime.now().timestamp()}_{len(self.logs)}"
        }

        self.logs.append(entry)

        # Manter apenas os logs mais recentes
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]

    def get_all_logs(self):
        """Retorna todos os logs"""
        return self.logs.copy()

    def filter_logs(self, level=None):
        """Filtra logs por nível"""
        if level is None or level == 'ALL':
            return self.logs.copy()

        return [log for log in self.logs if log['level'] == level.upper()]

    def clear(self):
        """Limpa todos os logs"""
        self.logs = []

    def export(self, filename=None):
        """Exporta logs para arquivo"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filename = f"logtudo-logs-{timestamp}.txt"

        content = '\n'.join(
            f"[{log['timestamp']}] [{log['level']:7}] {log['message']}"
            for log in self.logs
        )

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        return filename

    def toggle_auto_scroll(self):
        """Alterna auto-scroll"""
        self.auto_scroll = not self.auto_scroll
        return self.auto_scroll

    def log_step(self, step_name, step_number=None, total_steps=None):
        """Log de etapa de processamento"""
        if step_number and total_steps:
            message = f"Etapa {step_number}/{total_steps}: {step_name}"
        else:
            message = f"Etapa: {step_name}"

        self.info(message)

    def log_progress(self, current, total, message=""):
        """Log de progresso"""
        percent = (current / total * 100) if total > 0 else 0
        full_message = f"[{percent:5.1f}%] {message} ({current}/{total})"
        self.info(full_message)

    def log_error_with_context(self, error, context, suggestion=""):
        """Log de erro com contexto e sugestão"""
        self.error(f"{context}: {str(error)}")

        if suggestion:
            self.warning(f"Sugestão: {suggestion}")
