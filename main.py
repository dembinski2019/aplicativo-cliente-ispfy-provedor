from kivymd.app import MDApp
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.network.urlrequest import UrlRequest
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton,MDRaisedButton
from kivy.metrics import dp
from datetime import date
import json
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import FloatLayout
from kivymd.uix.list import MDList
from kivy.uix.scrollview import ScrollView
from api import URL,ROTA_LOGIN,password_md5,validation_user,HEADERS
from kivy.storage.jsonstore import JsonStore

global DB
DB = JsonStore('db.json')



class Manager(ScreenManager):
    pass


class AutorizationScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def entra(self,*args):
        self.parent.current = 'client_screen'

    def on_success(self, req, result):
        if result:
            DB['user'] = {'user':json.loads(result)}
            Clock.schedule_once(self.entra,.5)
    
    def on_failure(self,req, result):
        result = str(result)
        self.ids.error_login.text = result

    def on_error(self,req, result):
        result = str(result)
        self.ids.error_login.text = result 

    def login(self):
        u = self.ids.user.text 
        password = self.ids.password.text       
        user = validation_user(u)
        _pass = password_md5(password)
        data  = json.dumps({'login':user,'password':_pass})
        UrlRequest(
            url=URL+ROTA_LOGIN,req_body=data,
            req_headers=HEADERS,
            on_success=self.on_success,
            on_error=self.on_error,
            on_failure=self.on_failure
            )


class LinesBoleto(BoxLayout):
    confirmation = None
    def __init__(self,codigo, **kwargs):
        super().__init__( **kwargs)
        self.ids.cod_boleto.text = codigo
       
       
    def copiar(self, *args):
        self.ids.cod_boleto.select_all()
        self.ids.cod_boleto.copy()
        Clock.schedule_once(self.confimation_sucess,.2)


    def confimation_sucess(self,*args):
        if not self.confirmation:
            self.confirmation =  MDDialog(
                text = "Código copiado com Sucesso",
                type="alert",
                buttons = [
                    MDRaisedButton(text="Ok", 
                    on_release=lambda x: self.confirmation.dismiss()
                    )
                ]
            )
        self.confirmation.open()


class Content(BoxLayout):
    def __init__(self,items, **kwargs):
        self.orientation = "vertical"
        super().__init__( **kwargs)
        if type(items) == list:
            for codigo in items:
                self.add_widget(LinesBoleto(codigo))
        else:
            self.add_widget(LinesBoleto(items))
            

class ClientScreen(Screen):
    dialog = None

    def on_pre_enter(self,*args):
        """
            Função chamada antes do App entra na tela ClienteScreen,
            mostrando na tela o usuario ativo no aplicativo.
            Após chama a função get_boleto_aberto().
        """
        try:
            DB.delete(key='consulta_cobranca_aberto') 
            DB.delete(key="consulta_next_cobranca")
        except KeyError:
            pass
        self.user = DB.get("user")['user']
        if self.user:
            name = self.user['fantasia_apelido']
            if name == 'none':
                name = self.user['nome_razao']
            self.ids.client_name.text = f"{name.lower().capitalize()}!"
            self.get_cobranca_aberto()
            self.get_next_cobranca()


    def on_success_cobranca_aberto(self, req, result):
        """
            Função que recebe o retorno da função get_cobranca_aberto caso for sucesso
            Salvando no banco de dados e chamando a função de leitura da cobrança
        """
        if result:
            DB.put('consulta_cobranca_aberto',cobranca=result)
        Clock.schedule_once(self.read_boleto_aberto)


    def on_error_cobranca_aberto(self, req, result):
        """
            retorno da função get_cobranca_aberto() caso haja erro
        
        """
        print(result)


    def on_failure_cobranca_aberto(self, req,result):
        """
            retorno da função get_cobranca_aberto() caso haja o request falhe        
        """
        print(result)


    def read_boleto_aberto(self,*args):
        """
            Função que Mostra os boletos em atraso
            é chamada logo ao entrar no aplicativo.
        """
        try:
            obj_cobranca = DB.get('consulta_cobranca_aberto')['cobranca']
            if len(obj_cobranca) == 1:
                id_cobraca = obj_cobranca[0]['id']
                valor = obj_cobranca[0]['valor']
                self.ids.boleto_em_aberto.text = f'Boleto nº: {id_cobraca}'
                self.ids.valor_boleto_aberto.text = f'R$ {valor},00'
            elif len(obj_cobranca) > 1:
                total = 0
                for i in obj_cobranca:
                    total += int(i['valor'])
                self.ids.boleto_em_aberto.text = f'Total de Boletos em abertos {len(obj_cobranca)}'
                self.ids.valor_boleto_aberto.text = f'Totalizando R$ {total},00'
        except:
            self.ids.boleto_em_aberto.text = ""
            self.ids.valor_boleto_aberto.text = f'O Sistema não encontrou débitos'


    def get_cobranca_aberto(self):
        """
            Faz request na API com a query necessaria para consultar se tem cobranças em aberto no dia atual;
            Atravez do Id do cliente que é pego do banco de dados;
        """
        contrato = self.user['id']
        today = date.today()
        rota_cobrancas_abertos = f'/object/cliente/contrato/cobranca?filter=id_contrato:IN:{contrato}[AND]status:EQ:aberto[AND]data_vencimento:LT:{today}'
        UrlRequest(
            url=URL+rota_cobrancas_abertos,
            req_headers=HEADERS,
            on_success=self.on_success_cobranca_aberto,
            on_error=self.on_error_cobranca_aberto,
            on_failure=self.on_failure_cobranca_aberto)


    def on_success_print(self, req, result):
        if result:
            self.boleto = result.split("<br>")
            self.mostra_c_barra(self.boleto[:2])
    
    
    def on_error_print(self,req,result):
        print("errou",result)


    def on_failure_print(self,req,result):
        self.mostra_c_barra(result)
        

    def mostra_c_barra(self,resp):
        """
            Função que instancia uma caixa de dialogo;
            Com informações como: 
                Linha digitavel de até 2 boletos vencidos caso existir,
                linha digitavel do proximo boleto a vencer,
        """
        if not self.dialog:
            self.dialog = MDDialog(
                title = "Seu Boleto",
                auto_dismiss = False,
                type = 'custom',
                content_cls = Content(resp),
                buttons = [
                        MDFlatButton(text="Sair",on_press= lambda x: self.dialog.dismiss(), on_release=lambda x: self.close_dialog())
                    ]
                )
        self.dialog.open()
    

    def close_dialog(self, *args):
        self.dialog = None   


    def print_boleto_aberto(self, *args):
        """
            Faz um get para a API para pegar os boletos vencidos
        """
        doc = self.user["cpf_cnpj"]
        query = f'/tool/assinante/boleto?doc={doc}&status=vencido&tipo=linha'
        UrlRequest(
            url=URL+query,
            req_headers=HEADERS,
            on_success=self.on_success_print,
            on_error=self.on_error_print,
            on_failure=self.on_failure_print
            )


    def on_success_print_next_boleto(self, req, result):
        """
            Retorno da função print_next_boleto(), caso a requisição seja bem sucedida;
            chamando para a função mostra_c_barra uma única linha digitavel do proximo boleto a vencer;
        """
        next_boleto = result.split("<br>")
        self.mostra_c_barra(next_boleto[:1])


    def on_error_print_next_boleto(self,req,result):
        """
            retorno da função print_next_boleto() caso haja erro na requisição
        """
        print(result)


    def on_failure_print_next_boleto(self,req,result):
        """
            retorno da função print_next_boleto() caso haja falha na requisição
        """
        print(result)


    def print_next_boleto(self, *args):
        """
            Faz um get na Api, que retorna o proximo boleto a vencer;
            Retornando a linha digitavel para pagamento;
        """
        doc = self.user["cpf_cnpj"]
        query = f'/tool/assinante/boleto?doc={doc}&status=vincendo&tipo=linha'
        UrlRequest(
            url=URL+query,
            req_headers=HEADERS,
            on_success=self.on_success_print_next_boleto,
            on_error=self.on_error_print_next_boleto,
            on_failure=self.on_failure_print_next_boleto
            )    


    def on_success_next_cobranca(self, req, result):
        """
            Função que recebe o retorno da função get_next_cobranca caso for sucesso
            Salvando no banco de dados e chamando a função de leitura da cobrança
        """
        print
        if result:
            DB.put('consulta_next_cobranca',cobranca=result[0])
        Clock.schedule_once(self.read_next_cobrança)


    def on_error_next_cobranca(self, req, result):
        """
            retorno da função get_next_cobranca() caso haja erro
        
        """
        print(result)


    def on_failure_next_cobranca(self, req,result):
        """
            retorno da função get_next_cobranca() caso haja o request falhe        
        """
        print(result)


    def read_next_cobrança(self,*args):
        """
            Le o Banco de dados local e retorna os dados da proxima fatura para a tela.
        """
        try:
            obj_cobranca = DB.get('consulta_next_cobranca')['cobranca']
            id_cobraca = obj_cobranca['id']
            valor = obj_cobranca['valor']
            self.ids.next_cobrança.text = f'Boleto nº: {id_cobraca}'
            self.ids.next_cobrança_valor.text = f'R$ {valor},00'
        except:
            self.ids.next_cobrança.text = ""
            self.ids.next_cobrança_valor.text = f'Verifique com a central'


    def get_next_cobranca(self):
        """
            Faz request na API com a query necessaria para consultar a proxima fatura;
            Atravez do Id do cliente que é pego do banco de dados;
        """
        contrato = self.user['id']
        today = date.today()
        rota_cobrancas_abertos = f'/object/cliente/contrato/cobranca?filter=id_contrato:IN:{contrato}[AND]status:EQ:aberto[AND]data_vencimento:GTE:{today}'
        UrlRequest(
            url=URL+rota_cobrancas_abertos,
            req_headers=HEADERS,
            on_success=self.on_success_next_cobranca,
            on_error=self.on_error_next_cobranca,
            on_failure=self.on_failure_next_cobranca)


    def good_bay(self,*args):
        DB.clear()
        exit()


class MainScreen(Screen):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.inicialization, .2)


    def inicialization(self,*args):
        """
            Função que verifica se o Usuario já existe.
            Se sim, vai direto para a ClientScreen
        """
        try:
            if DB.get("user")['user']:
                self.ids.manager.current = "client_screen"  
        except:
            pass


class ContentNavigationDrawer(BoxLayout):
    

    def on_enter(self,*args):
        self.user = DB.get('user')['user']
        if self.user:
            self.ids.nav_name_client.text = self.user['nome_razao']
            self.ids.nav_id_numero.text = f"Id: {self.user['id']}"
            self.ids.nav_end_cliente.text = str(f"End:\
                                            \n{self.user['endereco_cobranca_rua']}\
                                            bairro:\n{self.user['endereco_cobranca_bairro']}"
                                            )
         
            
class Main(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"  
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.primary_hue = 'A400'
        self.theme_cls.accent_palette = 'Red'
        

if __name__ == "__main__":
    main = Main()
    main.run()  
