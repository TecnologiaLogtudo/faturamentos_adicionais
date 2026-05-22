# -*- coding: utf-8 -*-
"""
LoginWorkflow - Fluxo de Login
Gerencia o processo de autenticação no sistema LogTudo
"""


class LoginWorkflow:
    """Classe para gerenciar o fluxo de login"""

    def __init__(self, delay, gui, error_handler):
        """
        Inicializa o workflow de login

        Args:
            delay: Instância de Delay
            gui: Referência para a interface (para logs)
            error_handler: Instância de ErrorHandler
        """
        self.delay = delay
        self.gui = gui
        self.error_handler = error_handler
        self.steps = []

    def execute(self, page, settings):
        """
        Executa o processo de login

        Args:
            page: Página do Playwright
            settings: Dicionário com configurações (username, password)

        Returns:
            True se login bem-sucedido
        """
        self.gui.log("Iniciando processo de login...")

        try:
            # Navegar para página de login
            self.navigate_to_login(page)

            # Preencher credenciais
            self.fill_credentials(page, settings)

            # Submeter formulário
            self.submit_login(page)

            # Aguardar carregamento
            self.wait_for_login_complete(page)

            # Navegar para página de Conhecimentos após login
            self.navigate_to_conhecimentos(page)

            self.gui.log("Login realizado com sucesso", level="success")
            return True

        except Exception as e:
            error_msg = self.error_handler.handle('AUTH_ERROR', e, 'Processo de login')
            self.gui.log(f"Erro no login: {error_msg}", level="error")
            raise Exception(error_msg)

    def navigate_to_login(self, page):
        """Navega para página de login"""
        login_url = 'https://logtudo.e-login.net/?message_collection_id=msg_collection_69654311370983.91998362'

        self.gui.log(f"Navegando para: {login_url}")
        
        try:
            page.goto(login_url, wait_until='domcontentloaded', timeout=15000)
            self.gui.log("Página de login carregada")
            
            # Aguardar renderização rápida (load)
            try:
                page.wait_for_load_state('load', timeout=3000)
            except Exception:
                pass

        except Exception as e:
            self.gui.log(f"Erro ao carregar página de login: {e}", level="error")
            raise

        # Aplicar proteção anti-detecção
        self._apply_stealth_mode(page)

        # Aguardar campos de login aparecerem
        self.gui.log("Aguardando campos de login aparecerem...")
        try:
            page.wait_for_selector('input[name="usuario"]', state='visible', timeout=10000)
            self.gui.log("Campos de login detectados e visíveis")
        except Exception as e:
            self.gui.log(f"Timeout esperando campos de login: {e}", level="warning")

        # Extra delay para garantir que tudo renderizou
        self.delay.custom(1000)

    def fill_credentials(self, page, settings):
        """Preenche credenciais de login"""
        self.gui.log("Preenchendo credenciais...")

        try:
            # Preencher usuário de forma segura
            usuario_selector = 'input[name="usuario"]'
            self.gui.log(f"Aguardando campo de usuário...")
            page.wait_for_selector(usuario_selector, state='visible', timeout=10000)
            
            self.gui.log(f"Preenchendo usuário...")
            page.locator(usuario_selector).scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            page.click(usuario_selector, force=True)
            page.wait_for_timeout(200)
            page.fill(usuario_selector, settings['username'])
            
            self.gui.log(f"Usuário preenchido: {settings['username']}")
            self.delay.custom(1000)

            # Preencher senha de forma segura
            senha_selector = 'input[name="senha"]'
            self.gui.log(f"Aguardando campo de senha...")
            page.wait_for_selector(senha_selector, state='visible', timeout=10000)
            
            self.gui.log(f"Preenchendo senha...")
            page.locator(senha_selector).scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            page.click(senha_selector, force=True)
            page.wait_for_timeout(200)
            page.fill(senha_selector, settings['password'])
            
            self.gui.log("Senha preenchida")
            self.delay.custom(50)
            
        except Exception as e:
            raise Exception(f"Erro ao preencher credenciais: {str(e)}")

    def submit_login(self, page):
        """Submete formulário de login"""
        self.gui.log("Enviando formulário de login...")

        submitted = False

        # Tentar encontrar botão de submit
        submit_button = self.wait_for_submit_button(page)

        if submit_button:
            try:
                submit_button.scroll_into_view_if_needed()
                self.delay.custom(50)  # Delay mínimo
                submit_button.click(force=True)
                self.gui.log("Botão de login clicado")
                submitted = True
            except Exception as e:
                self.gui.log(f"Erro ao clicar botão: {e}", level="warning")

        # Se não conseguiu clicar botão, usar Enter
        if not submitted:
            try:
                self.gui.log("Tentando envio com Enter...")
                page.press('input[name="senha"]', 'Enter')
                self.gui.log("Enter pressionado")
                submitted = True
            except Exception as e:
                self.gui.log(f"Erro ao pressionar Enter: {e}", level="warning")

        # Aguardar resposta rápida do servidor (1s em vez de 3s)
        self.delay.custom(1000)

    def wait_for_login_complete(self, page):
        """Aguarda login ser completado - versão otimizada"""
        self.gui.log("Aguardando autenticação completa...")

        # Primeiro: aguardar que o campo de login desapareça (mais rápido - ~1-2s)
        try:
            page.wait_for_selector('input[name="usuario"]', state='hidden', timeout=5000)
            self.gui.log("✓ Autenticação confirmada")
            return
        except Exception:
            pass

        # Segundo: verificar mudança de URL para página logada (rápido - ~1s)
        try:
            page.wait_for_url(
                lambda url: any(path in url for path in ['trans_conhecimento', 'principal', 'dashboard']),
                timeout=3000
            )
            self.gui.log("✓ Login confirmado pela URL")
            return
        except Exception:
            pass

        # Terceiro: aguardar carregamento mínimo
        try:
            page.wait_for_load_state('load', timeout=2000)
        except Exception:
            pass

        # Verificação final rápida
        try:
            current_url = page.url
            if any(path in current_url for path in ['trans_conhecimento', 'principal', 'dashboard']):
                self.gui.log("✓ Login confirmado")
                return
        except:
            pass

        self.gui.log("Login concluído", level="debug")

        # Aguardar extra para garantir carregamento completo
        self.delay.page_load()

    def wait_for_field(self, page, selector):
        """Espera por campo de formulário com melhor tratamento"""
        self.gui.log(f"Aguardando campo: {selector}", level="debug")
        
        try:
            element = page.wait_for_selector(selector, state='visible', timeout=10000)

            if not element:
                raise Exception(f"Campo não encontrado: {selector}")

            # Garantir que o elemento está realmente visível e interativo
            page.locator(selector).scroll_into_view_if_needed()
            self.gui.log(f"Campo encontrado: {selector}", level="debug")

            return element

        except Exception as e:
            error_msg = f"Erro esperando campo {selector}: {str(e)}"
            self.gui.log(error_msg, level="error")
            raise Exception(error_msg)

    def wait_for_submit_button(self, page):
        """Espera por botão de submit"""
        button_selectors = [
            'input[type="submit"]',
            'button[type="submit"]',
            '.classBotao',
            'input[value*="Entrar"]',
            'input[value*="Login"]'
        ]

        for selector in button_selectors:
            try:
                button = page.wait_for_selector(selector, state='visible', timeout=3000)
                if button:
                    return button
            except:
                continue

        return None

    def check_if_logged_in(self, page):
        """Verifica se já está logado"""
        try:
            logged_out_selectors = [
                'input[name="usuario"]',
                'input[name="senha"]',
                '.login-form'
            ]

            for selector in logged_out_selectors:
                try:
                    page.wait_for_selector(selector, state='visible', timeout=2000)
                    return False  # Ainda na página de login
                except:
                    continue

            return True

        except Exception:
            return False

    def logout(self, page):
        """Realiza logout"""
        try:
            self.gui.log("Realizando logout...")

            logout_selectors = [
                'a[href*="logout"]',
                'a[href*="sair"]',
                '.logout',
                '.sair'
            ]

            for selector in logout_selectors:
                try:
                    button = page.wait_for_selector(selector, state='visible', timeout=2000)
                    if button:
                        button.click()
                        self.gui.log("Logout realizado")
                        return
                except:
                    continue

            self.gui.log("Botão de logout não encontrado", level="warning")

        except Exception as e:
            self.gui.log(f"Erro ao fazer logout: {e}", level="error")
    def _apply_stealth_mode(self, page):
        """Aplica modo invisível para evitar detecção de automação"""
        try:
            page.evaluate("""
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
            self.gui.log("Modo invisível aplicado com sucesso", level="debug")
        except Exception as e:
            self.gui.log(f"Aviso: Não foi possível aplicar modo invisível: {e}", level="warning")

    def navigate_to_conhecimentos(self, page):
        """Navega para página de Conhecimentos após login bem-sucedido"""
        conhecimentos_url = 'https://logtudo.e-login.net/versoes/versao5.0/rotinas/c.php?id=trans_conhecimento&menu=s'
        
        self.gui.log(f"Navegando para página de Conhecimentos...")
        self.gui.log(f"URL: {conhecimentos_url}")
        
        try:
            # Navegar para a página de conhecimentos
            page.goto(conhecimentos_url, wait_until='domcontentloaded', timeout=15000)
            self.gui.log("Página de Conhecimentos carregada (DOM pronto)")
            
            # Aguardar carregamento de rede completo
            self.gui.log("Aguardando renderização da página...")
            try:
                page.wait_for_load_state('load', timeout=5000)
            except Exception:
                pass
            
            self.gui.log("Página de Conhecimentos pronta", level="success")
            
        except Exception as e:
            raise Exception(f"Erro ao navegar para Conhecimentos: {str(e)}")