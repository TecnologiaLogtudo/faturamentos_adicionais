# -*- coding: utf-8 -*-
"""
Delay - Módulo de Pausas
Gerencia pausas entre etapas para evitar quebra da automação
"""

import asyncio
import time
import random


class Delay:
    """Classe para gerenciar pausas entre etapas"""

    def __init__(self):
        """Inicializa o gerenciador de delays"""
        self.app = None  # Referência para a instância da aplicação principal
        self.default_delay = 700  # 0.7 segundos
        self.network_delay = 3000   # 3 segundos para operações de rede
        self.animation_delay = 1000  # 1.0 segundos para animações
        self.page_load_delay = 2000  # 2 segundos para carregamento de página

    def standard(self):
        """Pausa padrão entre etapas"""
        self.custom(self.default_delay)

    def network(self):
        """Pausa para operações de rede"""
        self.custom(self.network_delay)

    def animation(self):
        """Pausa para animações"""
        self.custom(self.animation_delay)

    def page_load(self):
        """Pausa para carregamento de página"""
        self.custom(self.page_load_delay)

    def custom(self, milliseconds):
        """
        Pausa customizada em milissegundos, com verificação de estado de pausa.

        Args:
            milliseconds: Tempo de pausa em milissegundos
        """
        # Primeiro, verifica se a automação está em modo de pausa
        if self.app and hasattr(self.app, 'state') and self.app.state.get('is_paused'):
            while self.app.state.get('is_paused') and self.app.state.get('is_running'):
                time.sleep(0.5)  # Checa a cada 500ms se saiu da pausa
        
        # Se a automação foi parada durante a pausa, sai sem aplicar o delay
        if self.app and hasattr(self.app, 'state') and not self.app.state.get('is_running'):
            return

        # Aplica o delay normal se não estiver pausado
        time.sleep(max(0, milliseconds) / 1000)

    def random(self, min_ms=1000, max_ms=2000):
        """
        Pausa com variação aleatória

        Args:
            min_ms: Tempo mínimo em ms
            max_ms: Tempo máximo em ms
        """
        variation = random.randint(min_ms, max_ms)
        self.custom(variation)

    def exponential_backoff(self, attempt, base_delay=1000, max_delay=30000):
        """
        Pausa exponencial backoff para retentativas

        Args:
            attempt: Número da tentativa (0-indexed)
            base_delay: Delay base em ms
            max_delay: Delay máximo em ms

        Returns:
            O delay aplicado em ms
        """
        delay = min(base_delay * (2 ** attempt), max_delay)
        self.custom(delay)
        return delay

    def set_default_delay(self, ms):
        """
        Configura delay padrão

        Args:
            ms: Delay em milissegundos (mínimo 500)
        """
        self.default_delay = max(500, ms)

    def set_network_delay(self, ms):
        """
        Configura delay de rede

        Args:
            ms: Delay em milissegundos (mínimo 1000)
        """
        self.network_delay = max(1000, ms)

    async def async_standard(self):
        """Pausa padrão assíncrona"""
        await asyncio.sleep(self.default_delay / 1000)

    async def async_custom(self, milliseconds):
        """Pausa customizada assíncrona"""
        await asyncio.sleep(max(0, milliseconds) / 1000)

    def wait_until(self, condition_func, timeout_ms=30000, check_interval_ms=500):
        """
        Aguarda até que uma condição seja satisfeita

        Args:
            condition_func: Função que retorna True quando a condição é satisfeita
            timeout_ms: Timeout em milissegundos
            check_interval_ms: Intervalo de verificação em ms

        Returns:
            True se a condição foi satisfeita, False se houve timeout
        """
        start_time = time.time()
        timeout_seconds = timeout_ms / 1000
        check_interval = check_interval_ms / 1000

        while time.time() - start_time < timeout_seconds:
            if condition_func():
                return True
            time.sleep(check_interval)

        return False
