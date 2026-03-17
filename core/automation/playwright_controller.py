# -*- coding: utf-8 -*-
"""
PlaywrightController - Controlador do Playwright
Gerencia inicialização e controle do navegador
"""

from playwright.sync_api import sync_playwright
import logging


class PlaywrightController:
    """Classe para controlar o navegador Playwright"""

    def __init__(self):
        """Inicializa o controlador"""
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_initialized = False

    def start(self, headless=True, timeout=30000, record_video_dir=None):
        """
        Inicializa o Playwright e abre o navegador

        Args:
            headless: Se True, executa em modo headless (sem interface)
            timeout: Timeout em milissegundos

        Returns:
            Página do navegador
        """
        try:
            self.playwright = sync_playwright().start()
            
            # Iniciar navegador com configurações para evitar detecção de automação
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',  # Ocultar chromedriver
                    '--no-first-run',
                    '--no-default-browser-check',
                ]
            )
            
            # Criar contexto com User-Agent realista e headers
            context_args = {
                "viewport": {"width": 1280, "height": 720},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "extra_http_headers": {
                    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Cache-Control": "max-age=0",
                },
            }
            if record_video_dir:
                context_args["record_video_dir"] = record_video_dir

            self.context = self.browser.new_context(
                **context_args
            )
            
            self.page = self.context.new_page()
            
            # Ocultar sinais de automação via JavaScript
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pt-BR', 'pt', 'en-US', 'en'],
                });
                
                window.chrome = {
                    runtime: {}
                };
            """)
            
            self.page.set_default_timeout(timeout)
            self.page.set_default_navigation_timeout(timeout)

            self.is_initialized = True

            logging.info("Navegador Playwright iniciado com sucesso (anti-detecção ativo)")

            return self.page

        except Exception as e:
            logging.error(f"Erro ao iniciar Playwright: {e}")
            raise

    def navigate(self, url, wait_until='networkidle'):
        """
        Navega para uma URL

        Args:
            url: URL de destino
            wait_until: Estado de espera ('load', 'domcontentloaded', 'networkidle', 'commit')
        """
        if not self.page:
            raise Exception("Navegador não inicializado")

        self.page.goto(url, wait_until=wait_until)
        
        # Aguardar carregamento completo
        self._wait_for_page_ready(timeout=15000)
        
        # Re-aplicar proteções anti-detecção
        self._apply_stealth_mode()

    def wait_for_selector(self, selector, state='visible', timeout=10000):
        """
        Aguarda elemento estar visível

        Args:
            selector: Seletor CSS do elemento
            state: Estado ('attached', 'detached', 'visible', 'hidden')
            timeout: Timeout em milissegundos

        Returns:
            Elemento encontrado
        """
        return self.page.wait_for_selector(selector, state=state, timeout=timeout)

    def click(self, selector, timeout=10000, force=False):
        """
        Clica em elemento

        Args:
            selector: Seletor CSS do elemento
            timeout: Timeout em milissegundos
            force: Se True, força clique mesmo se não visível
        """
        self.page.click(selector, timeout=timeout, force=force)

    def fill(self, selector, value, timeout=10000):
        """
        Preenche campo

        Args:
            selector: Seletor CSS do elemento
            value: Valor a ser preenchido
            timeout: Timeout em milissegundos
        """
        self.page.fill(selector, str(value), timeout=timeout)

    def select_option(self, selector, value, timeout=10000):
        """
        Seleciona opção em select

        Args:
            selector: Seletor CSS do elemento
            value: Valor da opção
            timeout: Timeout em milissegundos
        """
        self.page.select_option(selector, value, timeout=timeout)

    def text_content(self, selector, timeout=10000):
        """
        Obtém texto de elemento

        Args:
            selector: Seletor CSS do elemento
            timeout: Timeout em milissegundos

        Returns:
            Texto do elemento
        """
        return self.page.text_content(selector, timeout=timeout)

    def get_attribute(self, selector, attribute, timeout=10000):
        """
        Obtém atributo de elemento

        Args:
            selector: Seletor CSS do elemento
            attribute: Nome do atributo
            timeout: Timeout em milissegundos

        Returns:
            Valor do atributo
        """
        return self.page.get_attribute(selector, attribute, timeout=timeout)

    def is_visible(self, selector, timeout=2000):
        """
        Verifica se elemento está visível

        Args:
            selector: Seletor CSS do elemento
            timeout: Timeout em milissegundos

        Returns:
            True se visível, False caso contrário
        """
        try:
            self.page.wait_for_selector(selector, state='hidden', timeout=timeout)
            return False
        except:
            return True

    def wait_for_load_state(self, state='networkidle', timeout=30000):
        """
        Aguarda estado de carregamento

        Args:
            state: Estado ('load', 'domcontentloaded', 'networkidle')
            timeout: Timeout em milissegundos
        """
        self.page.wait_for_load_state(state, timeout=timeout)

    def wait_for_url(self, url_pattern, timeout=30000):
        """
        Aguarda URL mudar para padrão específico

        Args:
            url_pattern: Padrão de URL (pode ser regex)
            timeout: Timeout em milissegundos
        """
        self.page.wait_for_url(url_pattern, timeout=timeout)

    def get_current_url(self):
        """Obtém URL atual"""
        if not self.page:
            return None
        return self.page.url()

    def evaluate(self, page_function, *args):
        """
        Avalia JavaScript na página

        Args:
            page_function: Função JavaScript
            args: Argumentos

        Returns:
            Resultado da avaliação
        """
        return self.page.evaluate(page_function, *args)

    def screenshot(self, filename='screenshot.png', full_page=False):
        """
        Faz screenshot da página

        Args:
            filename: Nome do arquivo
            full_page: Se True, captura página inteira
        """
        self.page.screenshot(path=filename, full_page=full_page)

    def close(self):
        """Fecha o navegador"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            self.is_initialized = False
            logging.info("Navegador fechado")

    def stop(self):
        """Para o Playwright"""
        self.close()
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
            logging.info("Playwright parado")

    def start_tracing(self):
        if not self.context:
            return
        try:
            self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        except Exception:
            pass

    def stop_tracing(self, path):
        if not self.context:
            return
        try:
            self.context.tracing.stop(path=path)
        except Exception:
            pass

    def is_ready(self):
        """Verifica se está inicializado"""
        return self.is_initialized and self.page is not None

    def _wait_for_page_ready(self, timeout=10000):
        """
        Aguarda a página estar completamente pronta
        
        Args:
            timeout: Timeout em milissegundos
        """
        try:
            # Aguardar networkidle para garantir carregamento completo
            self.page.wait_for_load_state('networkidle', timeout=timeout)
            logging.info("Página pronta (networkidle)")
        except Exception:
            try:
                # Fallback para domcontentloaded se networkidle falhar
                self.page.wait_for_load_state('domcontentloaded', timeout=5000)
                logging.info("Página pronta (domcontentloaded)")
            except Exception as e:
                logging.warning(f"Timeout aguardando carregamento: {e}")

    def safe_fill(self, selector, value, delay_ms=1000):
        """
        Preenche campo de forma segura com validação
        
        Args:
            selector: Seletor CSS do elemento
            value: Valor a ser preenchido
            delay_ms: Delay em ms após preencher
        """
        try:
            # Aguardar elemento estar visível
            self.page.wait_for_selector(selector, state='visible', timeout=10000)
            
            # Scroll para visualizar
            self.page.locator(selector).scroll_into_view_if_needed()
            
            # Pequeno delay para renderização
            self.page.wait_for_timeout(300)
            
            # Clicar para garantir foco
            self.page.click(selector, force=True)
            self.page.wait_for_timeout(200)
            
            # Limpar campo
            self.page.fill(selector, '')
            self.page.wait_for_timeout(200)
            
            # Digitar com delay entre caracteres
            self.page.locator(selector).type(str(value), delay=50)
            
            # Delay pós-preenchimento
            self.page.wait_for_timeout(delay_ms)
            
            logging.info(f"Campo preenchido: {selector}")
            return True
            
        except Exception as e:
            logging.error(f"Erro ao preencher campo {selector}: {e}")
            raise

    def safe_click(self, selector, delay_ms=500):
        """
        Clica em elemento de forma segura com validação
        
        Args:
            selector: Seletor CSS do elemento
            delay_ms: Delay em ms após clicar
        """
        try:
            # Aguardar elemento estar visível
            self.page.wait_for_selector(selector, state='visible', timeout=10000)
            
            # Scroll para visualizar
            self.page.locator(selector).scroll_into_view_if_needed()
            
            # Pequeno delay para renderização
            self.page.wait_for_timeout(300)
            
            # Clicar
            self.page.click(selector, force=True)
            
            # Delay pós-clique
            self.page.wait_for_timeout(delay_ms)
            
            logging.info(f"Elemento clicado: {selector}")
            return True
            
        except Exception as e:
            logging.error(f"Erro ao clicar em {selector}: {e}")
            raise

    def safe_select_option(self, selector, value, delay_ms=800):
        """
        Seleciona opção de forma segura
        
        Args:
            selector: Seletor CSS do elemento
            value: Valor a selecionar
            delay_ms: Delay em ms após selecionar
        """
        try:
            # Aguardar elemento estar visível
            self.page.wait_for_selector(selector, state='visible', timeout=10000)
            
            # Scroll para visualizar
            self.page.locator(selector).scroll_into_view_if_needed()
            
            # Pequeno delay para renderização
            self.page.wait_for_timeout(300)
            
            # Selecionar
            self.page.select_option(selector, value)
            
            # Delay pós-seleção
            self.page.wait_for_timeout(delay_ms)
            
            logging.info(f"Opção selecionada: {selector} = {value}")
            return True
            
        except Exception as e:
            logging.error(f"Erro ao selecionar opção em {selector}: {e}")
            raise

    def _apply_stealth_mode(self):
        """Aplica modo invisível para evitar detecção de automação"""
        try:
            self.page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
                
                window.chrome = {
                    runtime: {}
                };
            """)
        except:
            pass  # Pode falhar em algumas páginas

    def __enter__(self):
        """Contexto de entrada"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Contexto de saída"""
        self.stop()
        return False
